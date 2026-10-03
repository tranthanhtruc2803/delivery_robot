# ros_web_bridge.py
import rclpy
from rclpy.node import Node
from nav_msgs.msg import OccupancyGrid, Odometry
from geometry_msgs.msg import PoseStamped
from tf2_msgs.msg import TFMessage
import math

class ROSWebBridge(Node):
    def __init__(self):
        super().__init__('ros_web_bridge')
        self.map_data = None
        self.pose_data = {'x': 0.0, 'y': 0.0, 'angle': 0.0, 'speed': 0.0}

        # Subscriptions
        self.create_subscription(OccupancyGrid, '/map', self.map_callback, 10)
        self.create_subscription(TFMessage, '/tf', self.tf_callback, 10)
        self.create_subscription(PoseStamped, '/slam_toolbox/pose', self.pose_callback, 10)
        self.create_subscription(Odometry, '/odom', self.odom_callback, 10)

    def odom_callback(self, msg):
        # speed is in m/s, convert to cm/s
        self.pose_data['speed'] = msg.twist.twist.linear.x * 100.0

    def euler_from_quaternion(self, x, y, z, w):
        """Convert a quaternion into euler angles (roll, pitch, yaw)"""
        t3 = +2.0 * (w * z + x * y)
        t4 = +1.0 - 2.0 * (y * y + z * z)
        yaw_z = math.atan2(t3, t4)
        return math.degrees(yaw_z) # Return in degrees for the React UI

    def map_callback(self, msg):
        self.map_data = {
            'width': msg.info.width,
            'height': msg.info.height,
            'resolution': msg.info.resolution,
            'origin': {
                'x': msg.info.origin.position.x,
                'y': msg.info.origin.position.y
            },
            'data': list(msg.data)
        }

    def pose_callback(self, msg):
        q = msg.pose.orientation
        yaw = self.euler_from_quaternion(q.x, q.y, q.z, q.w)
        self.pose_data.update({
            'x': msg.pose.position.x,
            'y': msg.pose.position.y,
            'angle': yaw
        })

    def tf_callback(self, msg):
        for transform in msg.transforms:
            # When missing wheel encoders, SLAM toolbox publishes map->odom, and we fake odom->base_link.
            # So the robot's real movement is represented by the odom frame update!
            if transform.child_frame_id in ["base_link", "odom"]:
                t = transform.transform.translation
                q = transform.transform.rotation
                yaw = self.euler_from_quaternion(q.x, q.y, q.z, q.w)
                self.pose_data.update({
                    'x': t.x,
                    'y': t.y,
                    'angle': yaw
                })

# Global bridge node
bridge_node = None

def init_ros():
    global bridge_node
    if not rclpy.ok():
        rclpy.init()
    if bridge_node is None:
        bridge_node = ROSWebBridge()

def spin_once():
    if bridge_node is not None:
        rclpy.spin_once(bridge_node, timeout_sec=0.1)

def spin_forever():
    """Spin continuously without sleeping to avoid falling behind on high-frequency topics like /tf"""
    if bridge_node is not None:
        rclpy.spin(bridge_node)

def get_map():
    if bridge_node is None:
        return {}
    return bridge_node.map_data or {}

def get_pose():
    if bridge_node is None:
        return {}
    return bridge_node.pose_data or {}
