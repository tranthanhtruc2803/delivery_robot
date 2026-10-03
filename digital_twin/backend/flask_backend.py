from flask import Flask, jsonify, request, Response
from flask_cors import CORS
import threading
import time
import json
import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, String
from geometry_msgs.msg import Twist

try:
    from ros_web_bridge import init_ros, spin_forever, get_pose, get_map
    try:
        from process_map import get_processed_map_image
    except ImportError:
        get_processed_map_image = None
    ROS_AVAILABLE = True
except ImportError:
    ROS_AVAILABLE = False

app = Flask(__name__)
CORS(app)

import queue
cmd_queue = queue.Queue()
cargo_queue = queue.Queue()

class WebCargoPublisher(Node):
    def __init__(self):
        super().__init__('web_cargo_publisher')
        self.cargo_pub = self.create_publisher(Bool, '/cargo_box/command', 10)
        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.status_sub = self.create_subscription(Bool, '/esp32_status', self.status_callback, 10)
        self.log_sub = self.create_subscription(String, '/esp32_logs', self.log_callback, 10)
        self.esp32_connected = False
        self.logs = []
        self.timer = self.create_timer(0.1, self.check_queues)

    def check_queues(self):
        while not cmd_queue.empty():
            v, w = cmd_queue.get()
            msg = Twist()
            msg.linear.x = v
            msg.angular.z = w
            self.cmd_pub.publish(msg)
            
        while not cargo_queue.empty():
            open_box = cargo_queue.get()
            msg = Bool()
            msg.data = open_box
            self.cargo_pub.publish(msg)

    def log_callback(self, msg: String):
        self.logs.append(msg.data)
        if len(self.logs) > 100:
            self.logs = self.logs[-100:]

    def status_callback(self, msg: Bool):
        self.esp32_connected = msg.data

cargo_node = None

def start_ros_node():
    global cargo_node
    if ROS_AVAILABLE:
        init_ros()
    else:
        rclpy.init(args=None)
    cargo_node = WebCargoPublisher()
    
    if ROS_AVAILABLE:
        import ros_web_bridge
        from rclpy.executors import MultiThreadedExecutor
        executor = MultiThreadedExecutor()
        if ros_web_bridge.bridge_node is not None:
            executor.add_node(ros_web_bridge.bridge_node)
        executor.add_node(cargo_node)
        try:
            executor.spin()
        except Exception as e:
            print(f"Executor spin failed: {e}")
    else:
        try:
            rclpy.spin(cargo_node)
        except Exception as e:
            print(f"rclpy spin failed: {e}")
    print("ROS thread exited!")

ros_thread = threading.Thread(target=start_ros_node, daemon=True)
ros_thread.start()

# Helper to normalize pose for UI
def get_real_position():
    if not ROS_AVAILABLE:
        return {'x': 50, 'y': 50, 'angle': 0, 'speed': 0}
    pose = get_pose()
    if not pose or (abs(pose.get('x', 0)) < 0.001 and abs(pose.get('y', 0)) < 0.001):
        return {'x': 50, 'y': 50, 'angle': 0, 'speed': 0}
    return {
        'x': (pose.get('x', 0) * 5) + 50, 
        'y': (pose.get('y', 0) * 5) + 50,
        'angle': pose.get('angle', 0),
        'speed': pose.get('speed', 0)
    }

# API Endpoints
@app.route('/api/status', methods=['GET'])
def get_status():
    esp_conn = cargo_node.esp32_connected if cargo_node else False
    return jsonify({
        'status': 'online',
        'ros2_connected': ROS_AVAILABLE,
        'cargo_service': 'ready',
        'esp32_connected': esp_conn
    })

@app.route('/api/position', methods=['GET'])
def get_position():
    return jsonify({'position': get_real_position()})

@app.route('/api/uart', methods=['GET'])
def get_uart():
    logs = []
    if cargo_node:
        logs = cargo_node.logs.copy()
        cargo_node.logs.clear()
    return jsonify({'logs': logs})

@app.route('/api/map', methods=['GET'])
def map_endpoint():
    if not ROS_AVAILABLE or not get_processed_map_image:
        return jsonify({'error': 'Map service unavailable'}), 404
    img_data = get_processed_map_image()
    if not img_data:
        return jsonify({'error': 'No map data yet'}), 404
    return jsonify({
        'status': 'success',
        'map_data': img_data
    })

@app.route('/api/box', methods=['POST', 'OPTIONS'])
def toggle_box():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    data = request.get_json(silent=True) or {}
    open_box = data.get('open', True)
    
    if cargo_node:
        cargo_queue.put(open_box)
        return jsonify({'success': True, 'cargo_box': 'OPEN' if open_box else 'CLOSED'})
    return jsonify({'success': False, 'error': 'ROS node down'}), 500

@app.route('/api/control', methods=['POST', 'OPTIONS'])
def control():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    data = request.get_json(silent=True) or {}
    direction = data.get('direction')
    
    v = 0.0
    w = 0.0
    if direction == 'up': v = 0.3
    elif direction == 'down': v = -0.3
    elif direction == 'left': w = 0.5
    elif direction == 'right': w = -0.5
    elif direction == 'stop': v = 0.0; w = 0.0
    
    print(f"[UI Control] Direction: {direction} -> v: {v}, w: {w}")
    
    if cargo_node:
        cmd_queue.put((v, w))
    return jsonify({'success': True})

@app.route('/api/reconnect', methods=['POST', 'OPTIONS'])
def reconnect():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    # The esp32_serial_node auto-reconnects every 2 seconds if disconnected.
    # We just return success so the frontend knows we received the request.
    return jsonify({'success': True, 'message': 'Reconnect requested'})

if __name__ == '__main__':
    print("🚀 Flask Backend starting on http://0.0.0.0:5000...")
    app.run(host='0.0.0.0', port=5000, debug=False)
