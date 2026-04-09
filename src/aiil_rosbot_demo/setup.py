from setuptools import find_packages, setup
from glob import glob
import os

package_name = 'aiil_rosbot_demo'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',['resource/' + package_name]),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch')),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='AI Innovation Lab, RMIT University',
    maintainer_email='timothy.wiley@rmit.edu.au',
    description='The aiil_rosbot_demo package',
    license='RMIT IP - Not for distribution',
    # tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            f"best_effort_repeater = {package_name}.best_effort_repeater:main",
            f"camera_info_best_effort_repeater = {package_name}.camera_info_best_effort_repeater:main",
            f"depth_best_effort_repeater = {package_name}.depth_best_effort_repeater:main",
            f"cmd_vel = {package_name}.cmd_vel:main",
            f"goToPose = {package_name}.goToPose:main",
            f"nav2_example = {package_name}.nav2_example:main",
            f"rostutorial_sub = {package_name}.rostutorial_sub:main",
            f"rostutorial_pub = {package_name}.rostutorial_pub:main",
            f"pid = {package_name}.pid:main",
            f"publish_hazard = {package_name}.publish_hazard:main",
            f"publish_navpath = {package_name}.publish_navpath:main",
            f"transform = {package_name}.transform:main",
            f"waypoint = {package_name}.waypoint:main",
        ],
    },
)
