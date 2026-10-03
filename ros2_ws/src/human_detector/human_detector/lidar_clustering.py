import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from visualization_msgs.msg import Marker, MarkerArray
import numpy as np
from sklearn.cluster import DBSCAN
import math

class HumanDetector(Node):
    def __init__(self):
        super().__init__('human_detector')
        
        # 1. Subscribe to your RPLidar data
        self.subscription = self.create_subscription(
            LaserScan,
            '/scan',
            self.scan_callback,
            10)
            
        # 2. Publisher to show the detected humans in RViz as green markers
        self.publisher_ = self.create_publisher(MarkerArray, '/human_markers', 10)

    def scan_callback(self, msg):
        # Extract valid ranges (ignore 'inf' or zero readings from the LiDAR)
        angles = []
        ranges = []
        for i, r in enumerate(msg.ranges):
            if msg.range_min < r < msg.range_max:
                angles.append(msg.angle_min + i * msg.angle_increment)
                ranges.append(r)

        if not ranges:
            return

        # 3. Convert Polar (distance/angle) to Cartesian (X/Y)
        angles = np.array(angles)
        ranges = np.array(ranges)
        x = ranges * np.cos(angles)
        y = ranges * np.sin(angles)
        points = np.column_stack((x, y))

        # 4. Clustering: Group points that are closer than 0.2 meters to each other
        clustering = DBSCAN(eps=0.2, min_samples=3).fit(points)
        labels = clustering.labels_

        marker_array = MarkerArray()
        marker_id = 0

        # 5. Analyze each cluster to see if it matches a human leg size
        unique_labels = set(labels)
        for label in unique_labels:
            if label == -1:
                continue # Ignore noise

            # Get all points in this specific cluster
            cluster_points = points[labels == label]
            
            # Calculate the width of the cluster
            min_x, min_y = np.min(cluster_points, axis=0)
            max_x, max_y = np.max(cluster_points, axis=0)
            width = math.sqrt((max_x - min_x)**2 + (max_y - min_y)**2)

            # 6. Filter: A human leg/body is roughly between 10cm and 60cm wide
            if 0.10 < width < 0.60:
                # Find the center of the cluster
                center_x = np.mean(cluster_points[:, 0])
                center_y = np.mean(cluster_points[:, 1])

                # Create a visual marker for RViz
                marker = Marker()
                marker.header.frame_id = msg.header.frame_id
                marker.header.stamp = self.get_clock().now().to_msg()
                marker.ns = "humans"
                marker.id = marker_id
                marker.type = Marker.CYLINDER
                marker.action = Marker.ADD
                marker.pose.position.x = center_x
                marker.pose.position.y = center_y
                marker.pose.position.z = 0.5
                marker.scale.x = 0.3 # 30cm wide cylinder
                marker.scale.y = 0.3
                marker.scale.z = 1.0 # 1 meter tall
                marker.color.a = 1.0 # Solid
                marker.color.r = 0.0
                marker.color.g = 1.0 # Green color
                marker.color.b = 0.0
                
                marker_array.markers.append(marker)
                marker_id += 1

        # Publish the markers to RViz
        self.publisher_.publish(marker_array)

def main(args=None):
    rclpy.init(args=args)
    detector = HumanDetector()
    rclpy.spin(detector)
    detector.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
