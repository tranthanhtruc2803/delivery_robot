# September 9th System Debug & Update Log

## Executive Summary
**IMPORTANT NOTE:** As of the latest tests, the Jetson **STILL CANNOT control the ESP32**. The following document outlines the attempted fixes and diagnosed issues, but the core issue of the Jetson failing to establish bidirectional control with the ESP32 remains unresolved.

After a lengthy debugging session, we traced a series of hardware and software conflicts causing the RPLidar to stop spinning, the ESP32 to ignore motor commands, and the Web UI to return 404 errors for the map. 

The root of the issue was that the ESP32 was **not connected via USB (`/dev/ttyUSB1`)**, but rather directly wired to the Jetson Nano's GPIO header using UART2 (`/dev/ttyTHS1`). Our earlier automated port-scanning scripts were mistakenly looking for the ESP32 on USB hubs, causing severe port collisions with the Lidar.

## What We Fixed

### 1. Serial Port Collision & Jetson GPIO
- **The Issue:** The `esp32_serial_node.py` had a legacy loop (`ports_to_check`) that aggressively probed `/dev/ttyUSB0` (the Lidar's port). When the Jetson pinged the Lidar with motor commands (`F`, `B`), the Lidar locked up and stopped spinning.
- **The Fix:** We stripped the aggressive polling logic out of `esp32_serial_node.py` and configured `start_robot.launch.py` to correctly map the ESP32 to `/dev/ttyTHS1` (the Jetson's hardware UART pins).

### 2. ESP32 Arduino Protocol Mismatch
- **The Issue:** There was an experimental commit where `esp32_serial_node.py` tried to send JSON payloads (`{"v": 0.5, "w": 0.0}`) instead of the single ASCII characters (`F`, `B`, `L`, `R`, `S`) that the Arduino firmware was programmed to receive. Because the ESP32 only understands letters, it ignored the JSON.
- **The Fix:** We reverted `esp32_serial_node.py` back to the single-character ASCII protocol so the Python ROS 2 node and the Arduino C++ firmware are speaking the exact same language again.
- **CURRENT STATUS:** **NOT FIXED.** Despite reverting to the correct protocol, the Jetson STILL cannot control the ESP32. Commands are sent, but the ESP32 does not actuate the motors.

### 3. ESP32 Pin 12 Bootloop / Hardware Crash
- **The Issue:** The Rear-Right motor (`PIN_RR_A`) was accidentally wired/assigned to Pin 12. Pin 12 is an MTDI "Strapping Pin" on the ESP32. Sending PWM signals to this pin while the motor was drawing current caused the ESP32's power state to crash.
- **The Fix:** We moved `PIN_RR_A` back to Pin 4 in `esp32_delivery_chassis.ino` and updated the `stopAll()` array to match.
- **CURRENT STATUS:** **NOT FIXED.** Hardware crashes and lack of response persist.

### 4. "Stack Canary Watchpoint" Interrupt Storm
- **The Issue:** When testing the robot on the floor (under load), the brushed DC motors generated massive electrical EMF noise. This noise leaked into the unshielded wheel encoder wire (`PIN_ENCODER_B`), tricking the ESP32 into thinking the wheel was rotating millions of times per second. This starved the CPU and caused a fatal FreeRTOS stack crash (`IDLE1`).
- **The Fix:** We injected a 100-microsecond software debounce filter into the `encoderISR()` function. This filter mathematically blocks all high-frequency electrical noise, only registering genuine physical wheel clicks.

### 5. Missing SLAM Toolbox (Map 404 Errors)
- **The Issue:** The `slam_toolbox_node` was accidentally deleted from `start_robot.launch.py` during testing. Without SLAM Toolbox, the `/map` topic was never published, causing the Flask backend to endlessly throw `404 Not Found` errors to the React frontend.
- **The Fix:** We restored the `async_slam_toolbox_node` to the launch file.

## Next Steps
- **Re-flash the ESP32:** You **must** re-compile and upload the updated `esp32_delivery_chassis.ino` file via the Arduino IDE so the new debounce filter and Pin 4 mappings take effect.
- **Build ROS 2:** We have already run `colcon build --packages-select esp32_bridge` to apply the Python node fixes.
- **Launch:** Run `/home/tttruc/delivery_robot/start_robot.sh`. The ESP32 is now reading cleanly from the Jetson GPIO (`ttyTHS1`), the Lidar is isolated on `ttyUSB0`, and the SLAM map will generate normally.
