#!/bin/bash

echo "======================================================="
echo "Starting Delivery Robot Digital Twin System..."
echo "======================================================="

# Function to safely shut down all background processes when you press Ctrl+C
cleanup() {
    echo ""
    echo "======================================================="
    echo "Shutting down all systems..."
    echo "======================================================="
    
    # Kill direct background jobs started by this script
    kill $(jobs -p) 2>/dev/null
    
    # Explicitly hunt down any escaping zombie processes that spawned their own child threads
    pkill -f "slam_toolbox" 2>/dev/null
    pkill -f "rplidar_ros" 2>/dev/null
    pkill -f "python3 flask_backend.py" 2>/dev/null
    pkill -f "vite" 2>/dev/null
    pkill -f "tf2_ros" 2>/dev/null
    
    echo "Cleanup complete! Goodbye."
    exit
}

# Run cleanup to kill any old processes before starting
echo "Running initial cleanup..."
pkill -f "slam_toolbox" 2>/dev/null
pkill -f "rplidar_ros" 2>/dev/null
pkill -f "flask_backend" 2>/dev/null
pkill -f "vite" 2>/dev/null
pkill -f "tf2_ros" 2>/dev/null
pkill -f "esp32_serial_node" 2>/dev/null
fuser -k 5000/tcp 2>/dev/null
fuser -k 5173/tcp 2>/dev/null
fuser -k 5174/tcp 2>/dev/null
sleep 2

# Trap Ctrl+C (SIGINT) and call the cleanup function
trap cleanup SIGINT SIGTERM

# Ensure ROS 2 environment is sourced
source /opt/ros/humble/setup.bash
if [ -f "/home/tttruc/delivery_robot/ros2_ws/install/setup.bash" ]; then
    source /home/tttruc/delivery_robot/ros2_ws/install/setup.bash
fi

echo "[1/5] Starting LiDAR..."
ros2 launch rplidar_ros rplidar_a1_launch.py &
# Wait a moment to ensure LiDAR spins up
sleep 3

echo "[2/5] Starting TF Publishers (odom -> base_link -> laser)..."
ros2 run tf2_ros static_transform_publisher 0 0 0 0 0 0 base_link laser &
ros2 run tf2_ros static_transform_publisher 0 0 0 0 0 0 odom base_link &
sleep 1

echo "[2.5/5] Starting ESP32 Bridge..."
ros2 run esp32_bridge esp32_serial_node &
sleep 1

echo "[3/5] Starting SLAM Toolbox..."
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
    -p use_response_expansion:=true &
sleep 2

echo "[4/5] Starting Flask Backend..."
cd /home/tttruc/delivery_robot/digital_twin/backend
python3 flask_backend.py &
sleep 2

echo "[5/5] Starting React Frontend..."
cd /home/tttruc/delivery_robot/digital_twin/frontend
npm run dev -- --host 0.0.0.0 &

echo ""
echo "======================================================="
echo "ALL SYSTEMS GO! "
echo "Open your browser to: http://localhost:5173"
echo "Press Ctrl+C at any time to gracefully stop all processes."
echo "======================================================="
echo "Showing live logs below (mixed from all services):"
echo ""

# Wait infinitely for all background processes (keeps the script running)
wait
