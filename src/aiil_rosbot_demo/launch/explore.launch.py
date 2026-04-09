import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    aiil_rosbot_demo_dir = get_package_share_directory('aiil_rosbot_demo')
    explore_lite_launch = os.path.join(
        get_package_share_directory('explore_lite'), 'launch', 'explore.launch.py'
    )

    params_file = LaunchConfiguration('params_file')
    use_sim_time = LaunchConfiguration('use_sim_time', default='false')

    declare_params_file_cmd = DeclareLaunchArgument(
        'params_file',
        default_value=os.path.join(aiil_rosbot_demo_dir, 'config', 'explore.yaml'),
        description='Full path to the ROS2 parameters file to use for all launched nodes',
    )

    declare_use_sim_time_cmd = DeclareLaunchArgument(
        'use_sim_time', default_value='false', description='Use simulation (Gazebo) clock if true'
    )

    nav2_bringup_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(aiil_rosbot_demo_dir, 'launch', 'nav.launch.py')),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'params_file': params_file,
        }.items(),
    )

    explore_lite_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([explore_lite_launch]),
        launch_arguments={
            'use_sim_time': use_sim_time,
        }.items(),
    )

    ld = LaunchDescription()

    ld.add_action(declare_params_file_cmd)
    ld.add_action(declare_use_sim_time_cmd)

    ld.add_action(nav2_bringup_launch)
    ld.add_action(explore_lite_launch)

    return ld