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

# Utility rule file for cluster.

# Include any custom commands dependencies for this target.
include median/CMakeFiles/cluster.dir/compiler_depend.make

# Include the progress variables for this target.
include median/CMakeFiles/cluster.dir/progress.make

median/CMakeFiles/cluster: /home/mfilippov/CLionProjects/gedlib/median/bin/cluster_letter
median/CMakeFiles/cluster: /home/mfilippov/CLionProjects/gedlib/median/bin/clustering_tests
median/CMakeFiles/cluster: /home/mfilippov/CLionProjects/gedlib/median/bin/classification_tests

cluster: median/CMakeFiles/cluster
cluster: median/CMakeFiles/cluster.dir/build.make
.PHONY : cluster

# Rule to build all files generated by this target.
median/CMakeFiles/cluster.dir/build: cluster
.PHONY : median/CMakeFiles/cluster.dir/build

median/CMakeFiles/cluster.dir/clean:
	cd /home/mfilippov/CLionProjects/gedlib/cmake-build-debug/median && $(CMAKE_COMMAND) -P CMakeFiles/cluster.dir/cmake_clean.cmake
.PHONY : median/CMakeFiles/cluster.dir/clean

median/CMakeFiles/cluster.dir/depend:
	cd /home/mfilippov/CLionProjects/gedlib/cmake-build-debug && $(CMAKE_COMMAND) -E cmake_depends "Unix Makefiles" /home/mfilippov/CLionProjects/gedlib /home/mfilippov/CLionProjects/gedlib/median /home/mfilippov/CLionProjects/gedlib/cmake-build-debug /home/mfilippov/CLionProjects/gedlib/cmake-build-debug/median /home/mfilippov/CLionProjects/gedlib/cmake-build-debug/median/CMakeFiles/cluster.dir/DependInfo.cmake "--color=$(COLOR)"
.PHONY : median/CMakeFiles/cluster.dir/depend

