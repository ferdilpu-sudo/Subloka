cmake_minimum_required(VERSION 3.22.1)
project(subloka_asr LANGUAGES C CXX)
include(FetchContent)
set(BUILD_SHARED_LIBS OFF CACHE BOOL "" FORCE)
set(WHISPER_BUILD_TESTS OFF CACHE BOOL "" FORCE)
set(WHISPER_BUILD_EXAMPLES OFF CACHE BOOL "" FORCE)
set(WHISPER_BUILD_SERVER OFF CACHE BOOL "" FORCE)
set(GGML_OPENMP OFF CACHE BOOL "" FORCE)
set(GGML_NATIVE OFF CACHE BOOL "" FORCE)
set(GGML_CPU_ALL_VARIANTS OFF CACHE BOOL "" FORCE)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)
FetchContent_Declare(whisper
    GIT_REPOSITORY https://github.com/ggml-org/whisper.cpp.git
    GIT_TAG 927cfce34f31707e17f2bff35c349632fb9e2c3a
    GIT_PROGRESS TRUE)
FetchContent_MakeAvailable(whisper)
add_library(subloka_asr SHARED whisper_jni.cpp)
target_compile_features(subloka_asr PRIVATE cxx_std_17)
target_link_libraries(subloka_asr PRIVATE whisper android log)
