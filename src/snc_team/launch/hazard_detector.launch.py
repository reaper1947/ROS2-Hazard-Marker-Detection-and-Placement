from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, SetEnvironmentVariable
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node


def generate_launch_description():

    image_topic = "/oak/rgb/image_raw/compressed"
    image_topic_repeat = image_topic + "/repeat"
    use_compressed = "true"

    return LaunchDescription([
        SetEnvironmentVariable("RCUTILS_LOGGING_USE_STDOUT", "1"),
        SetEnvironmentVariable("RCUTILS_LOGGING_BUFFERED_STREAM", "0"),

        DeclareLaunchArgument("gui", default_value="true"),
        DeclareLaunchArgument("image_topic", default_value=image_topic),
        DeclareLaunchArgument("image_topic_repeat", default_value=image_topic_repeat),
        DeclareLaunchArgument("use_compressed", default_value=use_compressed),
        DeclareLaunchArgument(
            "objects_path",
            default_value="/home/ter/fastwork_robot/par_coursework/src/objects_example",
            description="Path to trained hazard marker images",
        ),
        DeclareLaunchArgument(
            "settings_path",
            default_value="~/.ros/find_object_2d.ini",
        ),
        DeclareLaunchArgument("hfov_deg", default_value="69.0"),
        DeclareLaunchArgument("image_width", default_value="640.0"),
        DeclareLaunchArgument("duplicate_threshold", default_value="0.5"),
        DeclareLaunchArgument("confirm_frames", default_value="3"),
        DeclareLaunchArgument("publish_rate", default_value="1.0"),

        # ── use_sim_time ──────────────────────────────────────────────────────
        DeclareLaunchArgument(
            "use_sim_time",
            default_value="true",
            description="Use simulation clock (/clock topic). Set false on real robot.",
        ),
        # ─────────────────────────────────────────────────────────────────────

        # find_object_2d — uses Reliable QoS, so it needs the repeater bridge
        Node(
            package="find_object_2d",
            executable="find_object_2d",
            name="find_object_2d",
            output="screen",
            parameters=[{
                "subscribe_depth": False,
                "gui": LaunchConfiguration("gui"),
                "objects_path": LaunchConfiguration("objects_path"),
                "settings_path": LaunchConfiguration("settings_path"),
                "use_sim_time": PythonExpression(
                    ["'", LaunchConfiguration("use_sim_time"), "' == 'true'"]
                ),
            }],
            remappings=[
                ("image", LaunchConfiguration("image_topic_repeat")),
            ],
        ),

        # BestEffortRepeater — bridges camera (best_effort) → find_object_2d (reliable)
        Node(
            package="aiil_rosbot_demo",
            executable="best_effort_repeater",
            name="best_effort_repeater",
            output="screen",
            parameters=[
                {"sub_topic_name": LaunchConfiguration("image_topic")},
                {"repeat_topic_name": LaunchConfiguration("image_topic_repeat")},
                {"use_compressed": LaunchConfiguration("use_compressed")},
                {
                    "use_sim_time": PythonExpression(
                        ["'", LaunchConfiguration("use_sim_time"), "' == 'true'"]
                    )
                },
            ],
        ),

        Node(
            package="snc_team",
            executable="hazard_detector",
            name="hazard_detector",
            output="screen",
            parameters=[{
                "hfov_deg": LaunchConfiguration("hfov_deg"),
                "image_width": LaunchConfiguration("image_width"),
                "duplicate_threshold": LaunchConfiguration("duplicate_threshold"),
                "confirm_frames": LaunchConfiguration("confirm_frames"),
                "publish_rate": LaunchConfiguration("publish_rate"),
                "use_sim_time": PythonExpression(
                    ["'", LaunchConfiguration("use_sim_time"), "' == 'true'"]
                ),
            }],
        ),
    ])
