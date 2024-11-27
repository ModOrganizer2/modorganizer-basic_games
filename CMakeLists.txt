cmake_minimum_required(VERSION 3.16)

if(DEFINED DEPENDENCIES_DIR)
	include(${DEPENDENCIES_DIR}/modorganizer_super/cmake_common/mo2.cmake)
else()
	include(${CMAKE_CURRENT_LIST_DIR}/../cmake_common/mo2.cmake)
endif()

project(basic_games LANGUAGES NONE)
add_custom_target(basic_games ALL)
mo2_configure_python(basic_games
	MODULE
	TRANSLATIONS OFF)
