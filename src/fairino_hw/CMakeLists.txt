cmake_minimum_required(VERSION 3.22)
project(fairino_hw)

find_package(ament_cmake REQUIRED)

# Install configuration files
install(DIRECTORY config description launch waypoints DESTINATION share/${PROJECT_NAME}/)

ament_package()
