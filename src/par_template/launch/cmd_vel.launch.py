from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration

def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('driveSpeed', default_value='0.75'),
        DeclareLaunchArgument('rotateSpeed', default_value='0.5'),
        
        Node(
            package='par_template',
            executable='cmd_vel',
            name='cmd_vel',
            output='screen',
            parameters=[
                {'driveSpeed': LaunchConfiguration('driveSpeed')},
                {'rotateSpeed': LaunchConfiguration('rotateSpeed')},
            ]
        ),
    ])
