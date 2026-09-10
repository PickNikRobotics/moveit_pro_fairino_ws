cmake_minimum_required(VERSION 3.22)
project(picknik_accessories)

find_package(ament_cmake REQUIRED)
# Trimmed for the Fairino workspace: dropped find_package(fanuc_lrmate200id_support)
# and the Fanuc MuJoCo mesh-copy block below — that support package is not present
# here and is unrelated to the RealSense sensor + camera-adapter bracket we use
# (installed via the `descriptions` directory below).

install(
  DIRECTORY
    descriptions
    macros
    mujoco_assets
  DESTINATION
    share/${PROJECT_NAME}
)

# (removed) Fanuc LRMate200iD MuJoCo asset copy — depended on fanuc_lrmate200id_support.

# TODO: is this lint process hanging somehow?
# if(BUILD_TESTING)
# find_package(ament_lint_auto REQUIRED)
# ament_lint_auto_find_test_dependencies()
# endif()

ament_environment_hooks("${CMAKE_CURRENT_SOURCE_DIR}/env-hooks/${PROJECT_NAME}.dsv.in")


ament_package()
