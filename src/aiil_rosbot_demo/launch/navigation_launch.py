# Copyright (c) 2018 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0

import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction, SetEnvironmentVariable
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import LoadComposableNodes, Node
from launch_ros.descriptions import ComposableNode
from nav2_common.launch import RewrittenYaml


def generate_launch_description():
    bringup_dir = get_package_share_directory('aiil_rosbot_demo')

    namespace = LaunchConfiguration('namespace')
    use_sim_time = LaunchConfiguration('use_sim_time')
    autostart = LaunchConfiguration('autostart')
    params_file = LaunchConfiguration('params_file')
    use_composition = LaunchConfiguration('use_composition')
    container_name = LaunchConfiguration('container_name')
    container_name_full = (namespace, '/', container_name)
    use_respawn = LaunchConfiguration('use_respawn')
    log_level = LaunchConfiguration('log_level')

    lifecycle_nodes = [
        'controller_server',
        'smoother_server',
        'planner_server',
        'behavior_server',
        'bt_navigator',
        'waypoint_follower',
        'velocity_smoother',
    ]

    # ------------------------------------------------------------------ #
    #  Remapping rules
    #
    #  Nav2 internal chain:
    #    controller_server  →  cmd_vel         (raw output)
    #    velocity_smoother  ←  cmd_vel         (input from controller)
    #    velocity_smoother  →  cmd_vel_smoothed (smoothed output)
    #
    #  Your robot expects:
    #    /diff_drive_controller/cmd_vel        (final command)
    #    /diff_drive_controller/odom           (odometry feedback)
    # ------------------------------------------------------------------ #
    tf_remappings = [
        ('/tf', 'tf'),
        ('/tf_static', 'tf_static'),
    ]

    # controller_server publishes raw cmd_vel → velocity_smoother picks it up
    # We keep this as the default relative topic so the two nodes talk to each other.
    # Only the FINAL output (cmd_vel_smoothed) goes to the hardware topic.
    controller_remappings = tf_remappings  # no extra remap needed here

    # velocity_smoother:
    #   input  : cmd_vel          (receives from controller_server — same node group)
    #   output : cmd_vel_smoothed → /diff_drive_controller/cmd_vel  (to hardware)
    #   odom   : /odom            → /diff_drive_controller/odom     (feedback)
    velocity_smoother_remappings = tf_remappings + [
        ('odom', '/odometry/filtered'),
        ('cmd_vel_smoothed', '/cmd_vel'),
    ]

    # bt_navigator needs the real odom topic for progress monitoring
    bt_navigator_remappings = tf_remappings + [
        ('odom', '/odometry/filtered'),
    ]

    # ------------------------------------------------------------------ #
    param_substitutions = {
        'use_sim_time': use_sim_time,
        'autostart': autostart,
    }

    configured_params = RewrittenYaml(
        source_file=params_file,
        root_key=namespace,
        param_rewrites=param_substitutions,
        convert_types=True,
    )

    # ================================================================== #
    #  Launch arguments
    # ================================================================== #
    return LaunchDescription([
        SetEnvironmentVariable('RCUTILS_LOGGING_BUFFERED_STREAM', '1'),

        DeclareLaunchArgument('namespace', default_value=''),
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        DeclareLaunchArgument('params_file',
                              default_value=os.path.join(bringup_dir, 'config', 'nav2_params.yaml')),
        DeclareLaunchArgument('autostart', default_value='true'),
        DeclareLaunchArgument('use_composition', default_value='False'),
        DeclareLaunchArgument('container_name', default_value='nav2_container'),
        DeclareLaunchArgument('use_respawn', default_value='False'),
        DeclareLaunchArgument('log_level', default_value='info'),

        # ============================================================== #
        #  Non-composed nodes
        # ============================================================== #
        GroupAction(
            condition=IfCondition(PythonExpression(['not ', use_composition])),
            actions=[

                # -- controller_server ----------------------------------
                # Publishes to relative 'cmd_vel'; velocity_smoother reads it.
                Node(
                    package='nav2_controller',
                    executable='controller_server',
                    output='screen',
                    respawn=use_respawn,
                    respawn_delay=2.0,
                    parameters=[configured_params],
                    arguments=['--ros-args', '--log-level', log_level],
                    remappings=controller_remappings,
                ),

                # -- smoother_server (path smoother, NOT velocity) ------
                Node(
                    package='nav2_smoother',
                    executable='smoother_server',
                    name='smoother_server',
                    output='screen',
                    respawn=use_respawn,
                    respawn_delay=2.0,
                    parameters=[configured_params],
                    arguments=['--ros-args', '--log-level', log_level],
                    remappings=tf_remappings,
                ),

                # -- planner_server ------------------------------------
                Node(
                    package='nav2_planner',
                    executable='planner_server',
                    name='planner_server',
                    output='screen',
                    respawn=use_respawn,
                    respawn_delay=2.0,
                    parameters=[configured_params],
                    arguments=['--ros-args', '--log-level', log_level],
                    remappings=tf_remappings,
                ),

                # -- behavior_server -----------------------------------
                Node(
                    package='nav2_behaviors',
                    executable='behavior_server',
                    name='behavior_server',
                    output='screen',
                    respawn=use_respawn,
                    respawn_delay=2.0,
                    parameters=[configured_params],
                    arguments=['--ros-args', '--log-level', log_level],
                    remappings=tf_remappings,
                ),

                # -- bt_navigator --------------------------------------
                Node(
                    package='nav2_bt_navigator',
                    executable='bt_navigator',
                    name='bt_navigator',
                    output='screen',
                    respawn=use_respawn,
                    respawn_delay=2.0,
                    parameters=[configured_params],
                    arguments=['--ros-args', '--log-level', log_level],
                    remappings=bt_navigator_remappings,
                ),

                # -- waypoint_follower ---------------------------------
                Node(
                    package='nav2_waypoint_follower',
                    executable='waypoint_follower',
                    name='waypoint_follower',
                    output='screen',
                    respawn=use_respawn,
                    respawn_delay=2.0,
                    parameters=[configured_params],
                    arguments=['--ros-args', '--log-level', log_level],
                    remappings=tf_remappings,
                ),

                # -- velocity_smoother ---------------------------------
                # Input  : cmd_vel          (from controller_server)
                # Output : cmd_vel_smoothed → /diff_drive_controller/cmd_vel
                # Odom   :                  → /diff_drive_controller/odom
                Node(
                    package='nav2_velocity_smoother',
                    executable='velocity_smoother',
                    name='velocity_smoother',
                    output='screen',
                    respawn=use_respawn,
                    respawn_delay=2.0,
                    parameters=[configured_params],
                    arguments=['--ros-args', '--log-level', log_level],
                    remappings=velocity_smoother_remappings,
                ),

                # -- lifecycle_manager ---------------------------------
                Node(
                    package='nav2_lifecycle_manager',
                    executable='lifecycle_manager',
                    name='lifecycle_manager_navigation',
                    output='screen',
                    arguments=['--ros-args', '--log-level', log_level],
                    parameters=[
                        {'use_sim_time': use_sim_time},
                        {'autostart': autostart},
                        {'node_names': lifecycle_nodes},
                    ],
                ),
            ],
        ),

        # ============================================================== #
        #  Composed nodes (use_composition:=True)
        # ============================================================== #
        LoadComposableNodes(
            condition=IfCondition(use_composition),
            target_container=container_name_full,
            composable_node_descriptions=[

                ComposableNode(
                    package='nav2_controller',
                    plugin='nav2_controller::ControllerServer',
                    name='controller_server',
                    parameters=[configured_params],
                    remappings=controller_remappings,
                ),
                ComposableNode(
                    package='nav2_smoother',
                    plugin='nav2_smoother::SmootherServer',
                    name='smoother_server',
                    parameters=[configured_params],
                    remappings=tf_remappings,
                ),
                ComposableNode(
                    package='nav2_planner',
                    plugin='nav2_planner::PlannerServer',
                    name='planner_server',
                    parameters=[configured_params],
                    remappings=tf_remappings,
                ),
                ComposableNode(
                    package='nav2_behaviors',
                    plugin='behavior_server::BehaviorServer',
                    name='behavior_server',
                    parameters=[configured_params],
                    remappings=tf_remappings,
                ),
                ComposableNode(
                    package='nav2_bt_navigator',
                    plugin='nav2_bt_navigator::BtNavigator',
                    name='bt_navigator',
                    parameters=[configured_params],
                    remappings=bt_navigator_remappings,
                ),
                ComposableNode(
                    package='nav2_waypoint_follower',
                    plugin='nav2_waypoint_follower::WaypointFollower',
                    name='waypoint_follower',
                    parameters=[configured_params],
                    remappings=tf_remappings,
                ),
                ComposableNode(
                    package='nav2_velocity_smoother',
                    plugin='nav2_velocity_smoother::VelocitySmoother',
                    name='velocity_smoother',
                    parameters=[configured_params],
                    remappings=velocity_smoother_remappings,
                ),
                ComposableNode(
                    package='nav2_lifecycle_manager',
                    plugin='nav2_lifecycle_manager::LifecycleManager',
                    name='lifecycle_manager_navigation',
                    parameters=[{
                        'use_sim_time': use_sim_time,
                        'autostart': autostart,
                        'node_names': lifecycle_nodes,
                    }],
                ),
            ],
        ),
    ])
