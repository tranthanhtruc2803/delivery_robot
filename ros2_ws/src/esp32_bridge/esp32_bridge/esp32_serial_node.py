import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, TransformStamped
from nav_msgs.msg import Odometry
from std_msgs.msg import Bool, String
import tf2_ros
import serial
import json
import math
import time

class ESP32SerialBridge(Node):
    def __init__(self):
        super().__init__('esp32_serial_bridge')

        # Parameters
        self.declare_parameter('port', '/dev/ttyUSB1')
        self.declare_parameter('baudrate', 115200)
        self.declare_parameter('odom_frame', 'odom')
        self.declare_parameter('base_frame', 'base_link')

        self.port = self.get_parameter('port').value
        self.baudrate = self.get_parameter('baudrate').value
        self.odom_frame = self.get_parameter('odom_frame').value
        self.base_frame = self.get_parameter('base_frame').value

        # Robot Pose tracking
        self.x = 0.0
        self.y = 0.0
        self.th = 0.0
        self.last_time = self.get_clock().now()

        self.last_cmd_vel_time = self.get_clock().now()
        self.last_cmd = 'S'

        # Serial Connection Setup
        try:
            # ttyTHS1 doesn't have DTR/RTS resets, but good practice
            self.ser = serial.Serial()
            self.ser.port = self.port
            self.ser.baudrate = self.baudrate
            self.ser.timeout = 0.1
            self.ser.open()
            self.get_logger().info(f"Connected to ESP32 on serial port {self.port} @ {self.baudrate}")
        except Exception as e:
            self.get_logger().warn(f"Could not open serial port {self.port}: {e}. Running in dummy mode.")
            self.ser = None

        # Subscriptions
        self.cmd_vel_sub = self.create_subscription(Twist, '/cmd_vel', self.cmd_vel_callback, 10)
        self.cargo_sub = self.create_subscription(Bool, '/cargo_box/command', self.cargo_callback, 10)

        # Publishers
        self.odom_pub = self.create_publisher(Odometry, '/odom', 10)
        self.log_pub = self.create_publisher(String, '/esp32_logs', 10)
        self.tf_broadcaster = tf2_ros.TransformBroadcaster(self)

        # Timers (Read serial and publish odom at 20Hz)
        self.create_timer(0.05, self.update_loop)

    def cmd_vel_callback(self, msg: Twist):
        self.last_cmd_vel_time = self.get_clock().now()
        v = msg.linear.x
        w = msg.angular.z
        cmd = 'S'
        if v > 0.1: cmd = 'F'
        elif v < -0.1: cmd = 'B'
        elif w > 0.1: cmd = 'L'
        elif w < -0.1: cmd = 'R'
        self.last_cmd = cmd
        self.get_logger().info(f"Received cmd_vel: v={v}, w={w} -> mapped to {cmd}")
        
        # INSTANTLY write movement commands to the serial port to prevent 
        # fast taps from being swallowed by the 50ms update_loop timer!
        if cmd != 'S' and self.ser and self.ser.is_open:
            try:
                self.ser.write(cmd.encode('ascii'))
            except Exception:
                pass

    def cargo_callback(self, msg: Bool):
        if self.ser and self.ser.is_open:
            cmd = 'O' if msg.data else 'C'
            try:
                self.ser.write(cmd.encode('ascii'))
                self.get_logger().info(f"Sent cargo door command: {'OPEN' if msg.data else 'CLOSE'}")
            except Exception as e:
                self.get_logger().error(f"Failed to write cargo command to serial: {e}")

    def update_loop(self):
        current_time = self.get_clock().now()
        dt = (current_time - self.last_time).nanoseconds / 1e9
        self.last_time = current_time

        # Send command to ESP32 continuously
        if self.ser and self.ser.is_open:
            if (current_time - self.last_cmd_vel_time).nanoseconds / 1e9 > 0.5:
                self.last_cmd = 'S'
            
            try:
                # Do NOT send 'S' to the ESP32. The ESP32 firmware has an automatic 1-second 
                # timeout that stops the motors. If we send 'S', it registers as a command 
                # and locks out the serial buffer for 1 full second, preventing new commands!
                if self.last_cmd != 'S':
                    self.ser.write(self.last_cmd.encode('ascii'))
                    #self.get_logger().info(f"Sent {self.last_cmd} to ESP32")
            except Exception as e:
                self.ser = None

        v_real = 0.0
        w_real = 0.0

        if self.ser and self.ser.is_open:
            try:
                line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    log_msg = String()
                    log_msg.data = f"< {line}"
                    self.log_pub.publish(log_msg)
                
                if line.startswith("v:"):
                    v_str = line.split(":")[1]
                    v_real = float(v_str) / 100.0  # Convert cm/s to m/s
                    # We don't get angular velocity from this firmware
                    w_real = 0.0
            except Exception:
                pass

        # Dead reckoning odometry integration
        delta_x = (v_real * math.cos(self.th)) * dt
        delta_y = (v_real * math.sin(self.th)) * dt
        delta_th = w_real * dt

        self.x += delta_x
        self.y += delta_y
        self.th += delta_th

        # Quaternion calculation
        qz = math.sin(self.th / 2.0)
        qw = math.cos(self.th / 2.0)

        # 1. Publish TF: odom -> base_link
        t = TransformStamped()
        t.header.stamp = current_time.to_msg()
        t.header.frame_id = self.odom_frame
        t.child_frame_id = self.base_frame
        t.transform.translation.x = self.x
        t.transform.translation.y = self.y
        t.transform.translation.z = 0.0
        t.transform.rotation.z = qz
        t.transform.rotation.w = qw
        self.tf_broadcaster.sendTransform(t)

        # 2. Publish Odometry message
        odom = Odometry()
        odom.header.stamp = current_time.to_msg()
        odom.header.frame_id = self.odom_frame
        odom.child_frame_id = self.base_frame
        odom.pose.pose.position.x = self.x
        odom.pose.pose.position.y = self.y
        odom.pose.pose.orientation.z = qz
        odom.pose.pose.orientation.w = qw
        odom.twist.twist.linear.x = v_real
        odom.twist.twist.angular.z = w_real
        self.odom_pub.publish(odom)

def main(args=None):
    rclpy.init(args=args)
    node = ESP32SerialBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
