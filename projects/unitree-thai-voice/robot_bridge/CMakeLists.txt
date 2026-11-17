cmake_minimum_required(VERSION 3.16)
project(g1_audio_bridge LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# CMAKE_PREFIX_PATH must point at the prefix where Unitree SDK2 was installed.
find_package(unitree_sdk2 REQUIRED CONFIG)

add_executable(g1_audio_bridge src/g1_audio_bridge.cpp)
target_link_libraries(g1_audio_bridge PRIVATE unitree_sdk2)
