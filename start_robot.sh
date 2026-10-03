#!/bin/bash

echo "======================================================="
echo "Starting Delivery Robot Autonomous System..."
echo "======================================================="

cleanup() {
    echo ""
    echo "======================================================="
    echo "Shutting down all systems gracefully..."
    echo "======================================================="
    
    kill $(jobs -p) 2>/dev/null
    pkill -f "ros2 launch" 2>/dev/null
    pkill -f "flask_backend.py" 2>/dev/null
    fuser -k 5000/tcp 2>/dev/null
    pkill -f "vite" 2>/dev/null
    
    echo "Cleanup complete! Goodbye."
    exit
}

trap cleanup SIGINT SIGTERM

source /opt/ros/humble/setup.bash
export PYTHONPATH=/opt/ros/humble/lib/python3.10/site-packages:$PYTHONPATH
source /home/tttruc/delivery_robot/ros2_ws/install/setup.bash

echo "[1/3] Launching ROS 2 Master Bringup (LiDAR, ESP32, TFs, Human Detector, Rosbridge)..."
ros2 launch delivery_robot_bringup start_robot.launch.py &
sleep 4

echo "[2/3] Starting Flask Web Backend..."
cd /home/tttruc/delivery_robot/digital_twin/backend
python3 flask_backend.py &
sleep 2

echo "[3/3] Starting React Digital Twin Frontend..."
cd /home/tttruc/delivery_robot/digital_twin/frontend
npm run dev -- --host 0.0.0.0 &

echo ""
echo "======================================================="
echo "ALL SYSTEMS OPERATIONAL! 🎉"
echo "Open Digital Twin Dashboard at: http://localhost:5173"
echo "Press Ctrl+C to stop all processes."
echo "======================================================="

wait
