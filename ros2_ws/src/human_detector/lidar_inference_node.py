import os
import sys
import numpy as np
from unittest.mock import MagicMock

# --- 1. THE "NO-TORCH" HACK ---
# This fakes the torch library so dataloader_basic.py can load without errors
mock_torch = MagicMock()
sys.modules["torch"] = mock_torch
sys.modules["torch.utils"] = MagicMock()
sys.modules["torch.utils.data"] = MagicMock()

class MockDataset: pass
sys.modules["torch.utils.data"].Dataset = MockDataset
# ------------------------------

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from visualization_msgs.msg import Marker, MarkerArray

# Ensure Python can find your 'utils' and 'data' folders
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(CURRENT_DIR)

import tensorrt as trt
import pycuda.driver as cuda
import pycuda.autoinit

# Import your original project files
from data.dataloader_basic import FrogDataLoader
from utils.postprocess import parse_loc

class LidarDetectionNode(Node):
    def __init__(self):
        super().__init__('lidar_detection_node')
        
        # --- CONFIGURATION ---
        self.engine_path = os.path.join(CURRENT_DIR, "lfe_ppn.engine")
        self.h5_path = os.path.join(CURRENT_DIR, "data/frog_16-41_test.h5")
        self.scan_len = 720  
        self.num_anchors = 30 
        
        # 2. INITIALIZE DATALOADER
        # Provides grid_polar and ANCHOR_REGRESSION_SCALE for coordinate transformation
        self.get_logger().info("Initializing DataLoader and Polar Grids...")
        self.loader = FrogDataLoader(self.h5_path, min_people=0)
        
        # 3. TENSORRT SETUP
        self.get_logger().info(f"Loading TensorRT Engine: {self.engine_path}")
        self.init_tensorrt()
        
        # 4. ROS TOPICS
        self.subscription = self.create_subscription(LaserScan, '/scan', self.scan_callback, 10)
        self.marker_pub = self.create_publisher(MarkerArray, '/detected_humans', 10)
        
        self.get_logger().info("🚀 LiDAR Human Detection Node is ONLINE!")

    def init_tensorrt(self):
        logger = trt.Logger(trt.Logger.WARNING)
        with open(self.engine_path, "rb") as f, trt.Runtime(logger) as runtime:
            self.engine = runtime.deserialize_cuda_engine(f.read())
            
        # Rename to self.trt_context to avoid ROS 2 property collision
        self.trt_context = self.engine.create_execution_context()
        
        # Memory allocations
        self.h_input = cuda.pagelocked_empty(self.scan_len, dtype=np.float32)
        self.d_input = cuda.mem_alloc(self.h_input.nbytes)

        output_shape = self.engine.get_tensor_shape("output_loc")
        self.h_output = cuda.pagelocked_empty(trt.volume(output_shape), dtype=np.float32)
        self.d_output = cuda.mem_alloc(self.h_output.nbytes)
        
        self.stream = cuda.Stream()

    def scan_callback(self, msg):
        # A. Preprocessing: Exact Angular Binning (NO INTERPOLATION)
        raw_ranges = np.array(msg.ranges)
        # NaN points should be treated as far away (e.g. 10.0m) to not create fake obstacles
        raw_ranges = np.nan_to_num(raw_ranges, nan=10.0, posinf=10.0, neginf=0.0)
        
        # 1. Calculate the exact angle for every raw point
        angles = msg.angle_min + np.arange(len(raw_ranges)) * msg.angle_increment
        
        # 2. Extract model bounds from the dataloader
        model_ang_min = self.loader.SCAN_ANGMIN
        model_ang_max = self.loader.SCAN_ANGMAX
        
        # 3. Create a clean array filled with "far away" background (10.0m)
        scan_720 = np.full(self.scan_len, 10.0, dtype=np.float32)
        
        # 4. Map physical points directly to their exact bins
        for i in range(len(angles)):
            # Ignore points outside the model's FOV (e.g., behind the robot) and far points
            if model_ang_min <= angles[i] <= model_ang_max and raw_ranges[i] <= 10.0:
                ratio = (angles[i] - model_ang_min) / (model_ang_max - model_ang_min)
                bin_idx = int(ratio * self.scan_len)
                
                # If multiple laser hits land in the same bin, keep the closest one
                if 0 <= bin_idx < self.scan_len:
                    if raw_ranges[i] < scan_720[bin_idx]:
                        scan_720[bin_idx] = raw_ranges[i]

        # B. Normalization (Crucial: must match training logic)[cite: 1]
        scan_norm = self.loader.normalize_scan(scan_720)

        # C. GPU Inference
        np.copyto(self.h_input, scan_norm.ravel())
        cuda.memcpy_htod_async(self.d_input, self.h_input, self.stream)
        
        self.trt_context.set_tensor_address("input_scan", int(self.d_input))
        self.trt_context.set_tensor_address("output_loc", int(self.d_output))
        self.trt_context.execute_async_v3(stream_handle=self.stream.handle)
        
        cuda.memcpy_dtoh_async(self.h_output, self.d_output, self.stream)
        self.stream.synchronize()

        # D. Post-processing: Reshape and Parse[cite: 1]
        # Reshape to (Sectors, Anchors, 3) to satisfy parse_loc indexing
        preds = self.h_output.reshape(-1, self.num_anchors, 3) 
        detections = parse_loc(self.loader, preds, threshold=0.95) 
        
        # Filter out false positives that are predicted beyond 10m
        valid_detections = []
        if detections is not None:
            for det in detections:
                dist = np.hypot(det[0], det[1])
                if dist <= 10.0:
                    valid_detections.append(det)
                    
        if len(valid_detections) == 0:
            valid_detections = None
        
        self.publish_markers(valid_detections)

    def publish_markers(self, detections):
        # --- THE SAFETY GATE ---
        if detections is None:
            # If no humans are detected, we still want to clear old markers
            # so the red cylinders don't "ghost" in the room.
            self.marker_pub.publish(MarkerArray())
            return
        # -----------------------

        marker_array = MarkerArray()
        for i, det in enumerate(detections):
            marker = Marker()
            marker.header.frame_id = "laser" # Must match your RPLIDAR Frame ID
            marker.header.stamp = self.get_clock().now().to_msg()
            marker.id = i
            marker.type = Marker.CYLINDER
            marker.action = Marker.ADD
            
            # Map detected X, Y to ROS world space
            marker.pose.position.x = float(det[0])
            marker.pose.position.y = float(det[1])
            marker.pose.position.z = 0.5
            
            marker.scale.x = 0.4
            marker.scale.y = 0.4
            marker.scale.z = 1.0
            
            marker.color.a = 0.8
            marker.color.r = 1.0 # Detection color: Red
            
            marker.lifetime.nanosec = int(2e8) # 200ms lifetime to prevent flickering
            marker_array.markers.append(marker)
            
        self.marker_pub.publish(marker_array)

def main(args=None):
    rclpy.init(args=args)
    node = LidarDetectionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
