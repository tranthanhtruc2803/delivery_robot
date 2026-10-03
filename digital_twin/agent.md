# Digital Twin Car Monitor - Context for Agents

## Architecture Overview

This project is a Digital Twin web application for an indoor robot using ROS 2, SLAM, and LiDAR.

1. **Frontend (React + Vite)**: 
   - A modern React web interface that visualizes the robot's state, displays the map, and provides control interfaces.
   - Typically runs on `http://0.0.0.0:5173`.
   - Source code located in `src/`.

2. **Backend (Python Flask)**:
   - `flask_backend.py`: Serves as the bridge between the React frontend and the robot's hardware/ROS 2 ecosystem.
   - Exposes REST API endpoints: `/api/position`, `/api/map`, `/api/control`, `/api/webcam`, and `/api/uart`.
   - Manages a background thread for UART serial communication to send literal directional commands and read logs.

3. **ROS 2 Integration (Humble)**:
   - `ros_web_bridge.py`: An embedded ROS 2 Node running inside the Flask backend. Subscribes to:
     - `/map` (`nav_msgs/OccupancyGrid`) for the SLAM map.
     - `/tf` (`tf2_msgs/TFMessage`) for tracking the `base_link` transform.
     - `/slam_toolbox/pose` (`geometry_msgs/PoseStamped`) for accurate odometry/pose.
   - Converts quaternions to euler angles for the UI.
   - `process_map.py`: Processes the raw occupancy grid array from ROS using OpenCV (morphological operations, Gaussian blurring) to create stylized walls (cyan) and free space (transparent blue), outputting a base64 encoded PNG for the React UI.

## Startup Sequence

**Recommended Method (Unified Script):**
A robust startup script has been created to launch all components and handle safe shutdown (killing zombie processes).
```bash
cd ~/Downloads/digital_twin
./start_robot.sh
```

**Manual Method (5 Terminals - Legacy/Debug):**
If you must run manually, use the following commands in separate terminals. *Note: Terminal 2 now requires TWO static transforms to fake odometry for SLAM Toolbox.*

**Terminal 1: Start LiDAR**
```bash
ros2 launch rplidar_ros rplidar_a1_launch.py
```

**Terminal 2: Static Transform Publishers**
```bash
ros2 run tf2_ros static_transform_publisher 0 0 0 0 0 0 base_link laser &
ros2 run tf2_ros static_transform_publisher 0 0 0 0 0 0 odom base_link
```

**Terminal 3: SLAM Toolbox**
```bash
ros2 run slam_toolbox async_slam_toolbox_node --ros-args \
-p use_sim_time:=false \
-p odom_frame:=odom \
-p base_frame:=base_link \
-p scan_topic:=/scan \
-p mode:=mapping \
-p correlation_search_space_dimension:=2.0 \
-p correlation_search_space_resolution:=0.02 \
-p loop_search_maximum_distance:=5.0 \
-p minimum_travel_distance:=0.0 \
-p minimum_travel_heading:=0.0 \
-p use_response_expansion:=true
```

**Terminal 4: Flask Backend**
```bash
source /opt/ros/humble/setup.bash
cd ~/Downloads/digital_twin
python3 flask_backend.py
```

**Terminal 5: React Frontend**
```bash
cd ~/Downloads/digital_twin
npm run dev -- --host 0.0.0.0
```

## UART Communication (Jetson to ESP32)

The Flask backend sends directional commands directly to an ESP32 microcontroller over UART.

- **Baud Rate**: `115200`
- **Jetson Port**: `/dev/ttyTHS1` (Pins 8 (TX) and 10 (RX) on the 40-pin header)
- **Protocol**: Single character commands sent without a newline (`F`, `B`, `L`, `R`, `S` for stop, `O` for box unlock).
- **Hardware Notes**:
  - Jetson TX (Pin 8) connects to ESP32 RX.
  - Jetson RX (Pin 10) connects to ESP32 TX.
  - A common Ground must be established between the Jetson and the ESP32.
  - **Important**: Avoid using Pins 16/17 on ESP32-WROVER boards as they are tied to internal PSRAM. Use alternative pins (e.g., 4 and 5) for `Serial2`.

## Recent Architectural Upgrades (July 2026)

1. **90s Minimal Purple Theme**: The UI was overhauled from a dark cyan aesthetic to a sleek, professional "Freeze Purple" and "Purple Pain" color scheme. The ROS `process_map.py` script was also updated to generate matching purple OpenCV images.
2. **Real-time Map Caching Fix**: React was aggressively caching the LiDAR images. Added cache-busting timestamp `?t=Date.now()` to the `/api/map` polling.
3. **SLAM Toolbox Zero-Odometry Fix**: The robot lacks wheel encoders, causing SLAM Toolbox to assume it was permanently stationary (`odom_frame:=base_link`), smearing the map and locking the coordinates at 0,0. This was fixed by:
   - Creating a fake `odom -> base_link` static transform.
   - Configuring SLAM Toolbox to use `odom_frame:=odom`.
   - Updating `ros_web_bridge.py` to intercept the `map -> odom` transform directly.
4. **ROS Thread Synchronization**: `spin_once` with artificial sleep was causing the Flask backend to choke on high-frequency `/tf` topics. Upgraded `ros_web_bridge.py` to use a dedicated `spin_forever()` thread.
5. **Robust Process Management**: Modified `start_robot.sh` to explicitly hunt and `pkill -f` zombies (like stray Flask or Vite nodes) upon `Ctrl+C` termination to prevent `Port 5000 is in use` errors.
6. **Delivery Box Security**: Added a PIN-protected unlock interface that transmits the `O` command over UART to trigger the servo mechanism on the ESP32.
