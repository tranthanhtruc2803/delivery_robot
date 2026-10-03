from setuptools import find_packages, setup

package_name = 'esp32_bridge'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools', 'pyserial'],
    zip_safe=True,
    maintainer='tttruc',
    maintainer_email='tttruc@todo.todo',
    description='Serial bridge node connecting ROS 2 to ESP32 differential chassis',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'esp32_serial_node = esp32_bridge.esp32_serial_node:main',
        ],
    },
)
