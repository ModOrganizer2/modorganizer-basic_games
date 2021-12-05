cmake_minimum_required(VERSION 3.16)

project(basic_games LANGUAGES CXX)
set(project_type python_module_plugin)
set(enable_warnings OFF)
set(create_translations OFF)

if(DEFINED DEPENDENCIES_DIR)
    include(${DEPENDENCIES_DIR}/modorganizer_super/cmake_common/project.cmake)
	include(${DEPENDENCIES_DIR}/modorganizer_super/cmake_common/src.cmake)
else()
	include(../cmake_common/project.cmake)
	include(../../cmake_common/src.cmake)
endif()
