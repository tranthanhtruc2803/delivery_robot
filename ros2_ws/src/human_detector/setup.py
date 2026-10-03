from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'human_detector'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'checkpoints'), glob('checkpoints/*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='tttruc',
    maintainer_email='tttruc@todo.todo',
    description='TensorRT LiDAR-based dynamic human detection node for delivery robot',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'lidar_inference_node = human_detector.lidar_inference_node:main',
        ],
    },
)
