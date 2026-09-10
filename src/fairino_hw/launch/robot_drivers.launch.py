from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import AnyLaunchDescriptionSource
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    """
    Persistent drivers for the Fairino FR5 hardware config.

    The Fairino arm driver itself is an in-process ros2_control system plugin
    (loaded via the URDF), so nothing is launched for the arm here. This persist
    launch brings up the wrist-mounted RealSense D415 camera stream so it runs
    for the life of the MoveIt Pro session.
    """
    fairino_hw_share = get_package_share_directory("fairino_hw")

    wrist_camera = IncludeLaunchDescription(
        AnyLaunchDescriptionSource(
            os.path.join(fairino_hw_share, "launch", "rs_cameras.launch.xml")
        )
    )

    return LaunchDescription([wrist_camera])
