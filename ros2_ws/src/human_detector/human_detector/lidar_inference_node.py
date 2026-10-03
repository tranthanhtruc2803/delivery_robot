import os
import sys
import numpy as np
from unittest.mock import MagicMock

# Fake PyTorch module for jetson environment without full PyTorch install
mock_torch = MagicMock()
sys.modules["torch"] = mock_torch
sys.modules["torch.utils"] = MagicMock()
sys.modules["torch.utils.data"] = MagicMock()

class MockDataset: pass
sys.modules["torch.utils.data"].Dataset = MockDataset

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan, PointCloud2, PointField
from geometry_msgs.msg import PoseArray, Pose
from visualization_msgs.msg import Marker, MarkerArray
import sensor_msgs_py.point_cloud2 as pc2
from std_msgs.msg import Header

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(CURRENT_DIR)

import tensorrt as trt
import pycuda.driver as cuda
import pycuda.autoinit

from ament_index_python.packages import get_package_share_directory
from human_detector.data.dataloader_basic import FrogDataLoader
from human_detector.utils.postprocess import parse_loc

class LidarDetectionNode(Node):
    def __init__(self):
        super().__init__('lidar_detection_node')
        share_dir = get_package_share_directory('human_detector')
        self.engine_path = os.path.join(share_dir, "checkpoints", "lfe_ppn.engine")
        if not os.path.exists(self.engine_path):
            # Fallback if running directly without install
            self.engine_path = os.path.join(CURRENT_DIR, "lfe_ppn.engine")

        self.h5_path = os.path.join(CURRENT_DIR, "data/frog_16-41_test.h5")
        self.scan_len = 720  
        self.num_anchors = 30 
        
        self.get_logger().info("Initializing DataLoader and Polar Grids...")
        self.loader = FrogDataLoader(self.h5_path, min_people=0)
        
        self.get_logger().info(f"Loading TensorRT Engine: {self.engine_path}")
        self.init_tensorrt()
        
        self.subscription = self.create_subscription(LaserScan, '/scan', self.scan_callback, 10)
        self.marker_pub = self.create_publisher(MarkerArray, '/detected_humans', 10)
        self.pose_pub = self.create_publisher(PoseArray, '/detected_humans_poses', 10)
        self.points_pub = self.create_publisher(PointCloud2, '/detected_humans_points', 10)
        
        self.get_logger().info("🚀 LiDAR Human Detection Node is ONLINE (Publishing PointCloud2 & PoseArray)!")

    def init_tensorrt(self):
        logger = trt.Logger(trt.Logger.WARNING)
        with open(self.engine_path, "rb") as f, trt.Runtime(logger) as runtime:
            self.engine = runtime.deserialize_cuda_engine(f.read())
            
        self.trt_context = self.engine.create_execution_context()
        
        self.h_input = cuda.pagelocked_empty(self.scan_len, dtype=np.float32)
        self.d_input = cuda.mem_alloc(self.h_input.nbytes)

        output_shape = self.engine.get_tensor_shape("output_loc")
        self.h_output = cuda.pagelocked_empty(trt.volume(output_shape), dtype=np.float32)
        self.d_output = cuda.mem_alloc(self.h_output.nbytes)
        
        self.stream = cuda.Stream()

    def scan_callback(self, msg):
        raw_ranges = np.array(msg.ranges)
        raw_ranges = np.nan_to_num(raw_ranges, nan=10.0, posinf=10.0, neginf=0.0)
        
        angles = msg.angle_min + np.arange(len(raw_ranges)) * msg.angle_increment
        model_ang_min = self.loader.SCAN_ANGMIN
        model_ang_max = self.loader.SCAN_ANGMAX
        
        scan_720 = np.full(self.scan_len, 10.0, dtype=np.float32)
        
        for i in range(len(angles)):
            if model_ang_min <= angles[i] <= model_ang_max and raw_ranges[i] <= 10.0:
                ratio = (angles[i] - model_ang_min) / (model_ang_max - model_ang_min)
                bin_idx = int(ratio * self.scan_len)
                
                if 0 <= bin_idx < self.scan_len:
                    if raw_ranges[i] < scan_720[bin_idx]:
                        scan_720[bin_idx] = raw_ranges[i]

        scan_norm = self.loader.normalize_scan(scan_720)

        np.copyto(self.h_input, scan_norm.ravel())
        cuda.memcpy_htod_async(self.d_input, self.h_input, self.stream)
        
        self.trt_context.set_tensor_address("input_scan", int(self.d_input))
        self.trt_context.set_tensor_address("output_loc", int(self.d_output))
        self.trt_context.execute_async_v3(stream_handle=self.stream.handle)
        
        cuda.memcpy_dtoh_async(self.h_output, self.d_output, self.stream)
        self.stream.synchronize()

        preds = self.h_output.reshape(-1, self.num_anchors, 3) 
        detections = parse_loc(self.loader, preds, threshold=0.95) 
        
        valid_detections = []
        if detections is not None:
            for det in detections:
                dist = np.hypot(det[0], det[1])
                if dist <= 10.0:
                    valid_detections.append(det)
                    
        if len(valid_detections) == 0:
            valid_detections = None
        
        self.publish_detections(valid_detections)

    def publish_detections(self, detections):
        stamp = self.get_clock().now().to_msg()
        header = Header(stamp=stamp, frame_id="laser")

        if detections is None:
            self.marker_pub.publish(MarkerArray())
            self.pose_pub.publish(PoseArray(header=header))
            fields = [PointField(name='x', offset=0, datatype=PointField.FLOAT32, count=1),
                      PointField(name='y', offset=4, datatype=PointField.FLOAT32, count=1),
                      PointField(name='z', offset=8, datatype=PointField.FLOAT32, count=1)]
            empty_pc = pc2.create_cloud(header, fields, [])
            self.points_pub.publish(empty_pc)
            return

        marker_array = MarkerArray()
        pose_array = PoseArray(header=header)
        points_list = []

        for i, det in enumerate(detections):
            x, y = float(det[0]), float(det[1])

            # 1. Marker
            marker = Marker()
            marker.header = header
            marker.id = i
            marker.type = Marker.CYLINDER
            marker.action = Marker.ADD
            marker.pose.position.x = x
            marker.pose.position.y = y
            marker.pose.position.z = 0.5
            marker.scale.x = 0.4
            marker.scale.y = 0.4
            marker.scale.z = 1.0
            marker.color.a = 0.8
            marker.color.r = 1.0
            marker.lifetime.nanosec = int(2e8)
            marker_array.markers.append(marker)

            # 2. Pose
            p = Pose()
            p.position.x = x
            p.position.y = y
            p.position.z = 0.0
            pose_array.poses.append(p)

            # 3. PointCloud2 (Represent human cylinder as obstacle points for Nav2)
            for z_off in np.linspace(0.0, 1.0, 5):
                points_list.append([x, y, z_off])

        fields = [PointField(name='x', offset=0, datatype=PointField.FLOAT32, count=1),
                  PointField(name='y', offset=4, datatype=PointField.FLOAT32, count=1),
                  PointField(name='z', offset=8, datatype=PointField.FLOAT32, count=1)]
        pc2_msg = pc2.create_cloud(header, fields, points_list)

        self.marker_pub.publish(marker_array)
        self.pose_pub.publish(pose_array)
        self.points_pub.publish(pc2_msg)

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
