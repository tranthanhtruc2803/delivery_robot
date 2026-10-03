import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, ExecuteProcess
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_xml.launch_description_sources import XMLLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time', default='false')

    # 1. RPLidar Launch
    rplidar_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('rplidar_ros'), 'launch', 'rplidar_a1_launch.py')
        )
    )

    # 2. Static Transforms (base_footprint -> base_link -> laser with physical offsets)
    tf_base_to_laser = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        arguments=['0.15', '0.0', '0.20', '0', '0', '0', 'base_link', 'laser']
    )

    tf_footprint_to_base = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        arguments=['0.0', '0.0', '0.05', '0', '0', '0', 'base_footprint', 'base_link']
    )

    # 3. ESP32 Serial Bridge Node
    esp32_bridge_node = Node(
        package='esp32_bridge',
        executable='esp32_serial_node',
        output='screen',
        parameters=[{'port': '/dev/ttyUSB1', 'baudrate': 115200}]
    )

    # 4. Human Detector Node
    human_detector_node = Node(
        package='human_detector',
        executable='lidar_inference_node',
        output='screen'
    )

    # 5. Rosbridge WebSocket
    rosbridge_node = IncludeLaunchDescription(
        XMLLaunchDescriptionSource(
            os.path.join(get_package_share_directory('rosbridge_server'), 'launch', 'rosbridge_websocket_launch.xml')
        )
    )

    # 6. SLAM Toolbox
    slam_toolbox_node = Node(
        package='slam_toolbox',
        executable='async_slam_toolbox_node',
        name='slam_toolbox',
        output='screen',
        parameters=[{
            'use_sim_time': False,
            'odom_frame': 'odom',
            'base_frame': 'base_link',
            'scan_topic': '/scan',
            'mode': 'mapping'
        }]
    )

    return LaunchDescription([
        rplidar_launch,
        tf_base_to_laser,
        tf_footprint_to_base,
        esp32_bridge_node,
        human_detector_node,
        rosbridge_node,
        slam_toolbox_node
    ])
