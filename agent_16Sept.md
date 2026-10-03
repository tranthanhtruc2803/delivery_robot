# Agent Handover - Sept 16

## The Big Target
The ultimate goal of this project is to build a **Human-Aware Navigation Delivery Robot**. 
The system features a digital twin web application that displays real-time telemetry (speed, LiDAR scan data map, robot orientation) and allows for manual teleoperation or autonomous navigation. 
The hardware runs on a **Jetson** (Ubuntu 22.04 / ROS 2 Humble) which handles the SLAM mapping via an RPLidar A1, and it communicates via USB Serial to an **ESP32**, which acts as the low-level motor chassis controller. The ESP32 is strictly read-only and handles 1-second burst movements based on received commands.

---

## What We Accomplished Today (v1.1)
Today's session focused heavily on achieving **perfect, zero-latency manual control** of the robot and fixing communication bugs across the stack.

1. **System Stability & Port Management**
   - Updated `start_robot.sh` to include aggressive `fuser` and `pkill` cleanups so the React frontend, Flask backend, and ROS nodes don't crash from ghost processes holding ports (5000, 5173).

2. **ROS 2 Thread Safety**
   - Originally, Flask was crashing with `RCLError` because worker threads were trying to publish ROS 2 messages directly.
   - We implemented a robust thread-safe `queue.Queue()` system in `flask_backend.py`. The Flask endpoints now push commands to the queue, and a dedicated ROS `Timer` running in the main thread safely pops and publishes the `Twist` messages.

3. **Flawless Teleoperation Control (The Swallowed Tap Bug)**
   - **The Bug:** The ESP32 firmware (`esp32_delivery_chassis.ino`) enforces a strict 1-second `COMMAND_DURATION` movement window, during which it actively discards all incoming serial bytes. The ROS bridge (`esp32_serial_node.py`) had a queue-polling timer running every 50ms. If a user tapped a UI button quickly, both `'F'` (Forward) and `'S'` (Stop) were sent to the ROS bridge instantly. The 50ms polling loop only saw the final `'S'`, effectively swallowing the command before it ever reached the ESP32. Additionally, sending `'S'` was triggering unnecessary 1-second lockouts on the ESP32.
   - **The Fix:** We completely removed the `'S'` command spam from the ROS node since the ESP32 auto-stops after 1 second anyway. We also modified `esp32_serial_node.py` so that the instant it receives a non-stop `cmd_vel` message, it writes it directly to the serial port immediately (bypassing the 50ms loop). This guarantees that every tap successfully reaches the ESP32's buffer. 

4. **Real-time Speed Dashboard**
   - Modified `ros_web_bridge.py` to actively subscribe to the `/odom` ROS topic and extract the real-time `linear.x` speed value calculated by the ESP32 wheel encoders.
   - Piped this speed data into the Flask `/api/position` endpoint.
   - Updated the React UI (`ControlPanel.tsx`) to display a sleek, real-time speed indicator (`cm/s`) directly in the control panel.

5. **Backup Created**
   - Created `deliver_robot_v1.0.zip` and `delivery_robot_v1.1.zip` as stable restore points.

---

## Architecture & Codebase Breakdown
To ensure smooth development tomorrow, here is a detailed functional breakdown of the current codebase and strict rules on what can and cannot be modified.

### 🚫 STRICTLY OFF-LIMITS (Do NOT Modify)
* **`esp32_firmware/esp32_delivery_chassis.ino`**
  * **Role:** The low-level hardware controller running on the ESP32.
  * **Function:** Reads serial commands (`F`, `B`, `L`, `R`, `S`) from the Jetson via USB. When a movement command is received, it locks the motors on for exactly 1 second (`COMMAND_DURATION`) and *actively discards* any incoming serial data during that time. After 1 second, it automatically stops the motors. It also reads wheel encoders and publishes speed (`v: X.XX`) back over the serial line.
  * **Why it's off-limits:** This is the physical firmware flashed to the microcontroller. Changing it requires physical access to re-flash the board, which we are avoiding. All logic fixes must be handled upstream on the Jetson/Web App.

### 🟢 SAFE TO MODIFY (Current Workspaces)
* **`ros2_ws/src/esp32_bridge/esp32_bridge/esp32_serial_node.py`**
  * **Role:** The ROS 2 to Serial bridge.
  * **Function:** Subscribes to `/cmd_vel` Twist messages and translates them into ASCII characters (`F`, `B`, `L`, `R`) for the ESP32. It also reads the incoming `v: X.XX` speed strings from the ESP32 and publishes them as standard ROS 2 `/odom` messages.
  * **Key Logic Added Today:** Bypassed the 50ms polling loop for outgoing commands. Now, it writes non-stop commands *instantly* to the serial buffer upon receiving a `/cmd_vel` message to prevent fast UI taps from being swallowed by the ROS queue. It intentionally avoids sending `'S'` commands to prevent triggering unnecessary 1-second ESP32 lockouts.

* **`digital_twin/backend/flask_backend.py`**
  * **Role:** The REST API and ROS 2 middleware.
  * **Function:** Exposes HTTP endpoints (`/api/control`, `/api/position`, `/api/uart`) for the React frontend. 
  * **Key Logic Added Today:** Implemented thread-safe `queue.Queue()` for handling UI commands. A ROS `Timer` in the main thread safely drains the queue and publishes `Twist` messages to `/cmd_vel`. It also packages the real-time `speed` (from `ros_web_bridge.py`) into the `/api/position` JSON payload.

* **`digital_twin/backend/ros_web_bridge.py`**
  * **Role:** Subscribes to complex ROS 2 topics and stores state for Flask.
  * **Function:** Listens to `/map` (OccupancyGrid), `/tf` (Transforms for position), and `/odom` (Odometry). 
  * **Key Logic Added Today:** Added a subscription to `/odom` to extract `msg.twist.twist.linear.x`, converting it from m/s to cm/s, and storing it for the Flask backend to serve as the live speed reading.

* **`digital_twin/frontend/src/app/components/ControlPanel.tsx`**
  * **Role:** The manual teleoperation UI.
  * **Function:** Provides on-screen buttons for driving the robot. 
  * **Key Logic Added Today:** Added a live `{speed} cm/s` indicator pill to the top right of the controls card.

* **`digital_twin/start_robot.sh`**
  * **Role:** The master boot script.
  * **Function:** Cleans up old processes (via `pkill` and `fuser`), sources the ROS 2 workspaces, and launches LiDAR, TF publishers, the ESP32 bridge, SLAM Toolbox, the Flask backend, and the React frontend in the background.

---

## Pending Tasks For Tomorrow
Now that the manual control and foundational ROS-web communication are solid, the next steps are to tackle the human-aware intelligence:

1. **Integrate Human Detection**
   - Use the RPLidar A1 data (or other sensors if added) on the Jetson to detect humans in the robot's path.
   - This might involve running a ROS 2 package for leg/obstacle detection that tracks dynamic obstacles.

2. **Smart Human-Aware Navigation**
   - Implement the navigation logic where the robot respects human presence.
   - The robot should dynamically alter its trajectory, slow down, or stop completely when a human is detected in its path.
   - This will involve integrating Nav2 with custom costmaps or behavior trees to prioritize human safety over optimal pathing.
