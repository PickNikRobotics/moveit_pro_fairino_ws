from launch import LaunchDescription
from launch_ros.actions import Node
from moveit_studio_utils_py.system_config import SystemConfigParser


def generate_launch_description():
    system_config_parser = SystemConfigParser()
    hardware_config = system_config_parser.get_hardware_config()

    # Extract robot_ip from urdf_params, defaulting to 192.168.58.2
    robot_ip = next(
        (
            param.get("robot_ip")
            for param in hardware_config.robot_description.urdf_params
            if "robot_ip" in param
        ),
        "192.168.58.2",
    )

    return LaunchDescription(
        [
            Node(
                package="fairino_hardware",
                executable="ros2_cmd_server",
                name="fr_command_server",
                output="screen",
                parameters=[
                    {"robot_ip": robot_ip},
                ],
            ),
        ]
    )
