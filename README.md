# Delivery Robot System v1.1

## Features in this Version
This version (v1.1) marks a stable milestone with the following fully functional features:

1. **Perfect Control Movement**: 
   - Instant responsiveness with no "swallowed" commands.
   - Fixed race conditions in the ROS `esp32_serial_node.py` queue. 
   - Commands are streamed immediately to the ESP32 buffer, bypassing polling delays and providing flawless manual teleoperation via the React UI.

2. **Real-time Speed Reading**: 
   - The React UI features a live speed indicator (cm/s).
   - ESP32 hardware encoders calculate speed, which is sent over USB serial to the ROS bridge, converted into `Odometry` messages, and served directly to the web dashboard via Flask.

3. **Live LiDAR Scanning**: 
   - The RPLidar A1 successfully captures real-time 2D scan data.
   - SLAM Toolbox translates this scan data into an `OccupancyGrid` map.
   - The Flask backend converts this grid into a visual map and serves it dynamically to the React frontend.

## Quick Start
To launch the entire stack (LiDAR, SLAM, TF, ESP32 Bridge, Flask, and React):
```bash
cd ~/delivery_robot/digital_twin
./start_robot.sh
```
Then open your browser to `http://localhost:5173`.
