# CMAKE generated file: DO NOT EDIT!
# Generated by "Unix Makefiles" Generator, CMake Version 3.30

# Delete rule output on recipe failure.
.DELETE_ON_ERROR:

#=============================================================================
# Special targets provided by cmake.

# Disable implicit rules so canonical targets will work.
.SUFFIXES:

# Disable VCS-based implicit rules.
% : %,v

# Disable VCS-based implicit rules.
% : RCS/%

# Disable VCS-based implicit rules.
% : RCS/%,v

# Disable VCS-based implicit rules.
% : SCCS/s.%

# Disable VCS-based implicit rules.
% : s.%

.SUFFIXES: .hpux_make_needs_suffix_list

# Command-line flag to silence nested $(MAKE).
$(VERBOSE)MAKESILENT = -s

#Suppress display of executed commands.
$(VERBOSE).SILENT:

# A target that is always out of date.
cmake_force:
.PHONY : cmake_force

#=============================================================================
# Set environment variables for the build.

# The shell in which to execute make rules.
SHELL = /bin/sh

# The CMake executable.
CMAKE_COMMAND = /opt/clion-2024.3.2/bin/cmake/linux/x64/bin/cmake

# The command to remove a file.
RM = /opt/clion-2024.3.2/bin/cmake/linux/x64/bin/cmake -E rm -f

# Escaping for special characters.
EQUALS = =

# The top-level source directory on which CMake was run.
CMAKE_SOURCE_DIR = /home/mfilippov/CLionProjects/gedlib

# The top-level build directory on which CMake was run.
CMAKE_BINARY_DIR = /home/mfilippov/CLionProjects/gedlib/cmake-build-debug

# Utility rule file for pvldb2020.

# Include any custom commands dependencies for this target.
include tests/pvldb2020/CMakeFiles/pvldb2020.dir/compiler_depend.make

# Include the progress variables for this target.
include tests/pvldb2020/CMakeFiles/pvldb2020.dir/progress.make

tests/pvldb2020/CMakeFiles/pvldb2020: /home/mfilippov/CLionProjects/gedlib/tests/pvldb2020/bin/test_lsape_enum

pvldb2020: tests/pvldb2020/CMakeFiles/pvldb2020
pvldb2020: tests/pvldb2020/CMakeFiles/pvldb2020.dir/build.make
.PHONY : pvldb2020

# Rule to build all files generated by this target.
tests/pvldb2020/CMakeFiles/pvldb2020.dir/build: pvldb2020
.PHONY : tests/pvldb2020/CMakeFiles/pvldb2020.dir/build

tests/pvldb2020/CMakeFiles/pvldb2020.dir/clean:
	cd /home/mfilippov/CLionProjects/gedlib/cmake-build-debug/tests/pvldb2020 && $(CMAKE_COMMAND) -P CMakeFiles/pvldb2020.dir/cmake_clean.cmake
.PHONY : tests/pvldb2020/CMakeFiles/pvldb2020.dir/clean

tests/pvldb2020/CMakeFiles/pvldb2020.dir/depend:
	cd /home/mfilippov/CLionProjects/gedlib/cmake-build-debug && $(CMAKE_COMMAND) -E cmake_depends "Unix Makefiles" /home/mfilippov/CLionProjects/gedlib /home/mfilippov/CLionProjects/gedlib/tests/pvldb2020 /home/mfilippov/CLionProjects/gedlib/cmake-build-debug /home/mfilippov/CLionProjects/gedlib/cmake-build-debug/tests/pvldb2020 /home/mfilippov/CLionProjects/gedlib/cmake-build-debug/tests/pvldb2020/CMakeFiles/pvldb2020.dir/DependInfo.cmake "--color=$(COLOR)"
.PHONY : tests/pvldb2020/CMakeFiles/pvldb2020.dir/depend

