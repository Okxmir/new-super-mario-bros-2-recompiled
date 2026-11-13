cmake_minimum_required(VERSION 3.24)
if(POLICY CMP0141)
    cmake_policy(SET CMP0141 NEW)
endif()
set(CMAKE_MSVC_DEBUG_INFORMATION_FORMAT "$<$<CONFIG:Debug,RelWithDebInfo>:Embedded>")
set(CMAKE_TRY_COMPILE_CONFIGURATION Release)
project(NewSuperMarioBros2Native LANGUAGES C CXX)

if(NOT WIN32 OR NOT MSVC OR NOT CMAKE_SIZEOF_VOID_P EQUAL 8)
    message(FATAL_ERROR "Use the Windows x64 MSVC toolchain")
endif()

set(CMAKE_C_STANDARD 17)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(UPSTREAM "${CMAKE_CURRENT_SOURCE_DIR}/build/upstream")
set(RUNTIME "${CMAKE_CURRENT_BINARY_DIR}/runtime")
set(GENERATED "${CMAKE_CURRENT_SOURCE_DIR}/generated/nsmb2-eur")
set(SDL3_DIR "${UPSTREAM}/SDL3-3.4.0/cmake")
find_package(Python3 REQUIRED COMPONENTS Interpreter)
find_package(SDL3 REQUIRED CONFIG COMPONENTS SDL3)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS tools/prepare_runtime.py)
execute_process(
    COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tools/prepare_runtime.py"
            "${UPSTREAM}/clockwork-master/runtime" "${RUNTIME}"
    COMMAND_ERROR_IS_FATAL ANY
)

file(GLOB TRANSLATED_CODE CONFIGURE_DEPENDS "${GENERATED}/*.c")
if(NOT TRANSLATED_CODE)
    message(FATAL_ERROR "Prepare the cartridge with scripts/prepare.ps1 before building")
endif()
add_library(game_code OBJECT ${TRANSLATED_CODE})
target_include_directories(game_code PRIVATE "${RUNTIME}/include" "${GENERATED}")
target_compile_definitions(game_code PRIVATE RECOMP_TRACE_CALLS)
target_compile_options(game_code PRIVATE /bigobj /fp:precise /w)
option(NSMB2_FAST_BUILD "Disable optimization for shorter iteration builds" ON)
if(NSMB2_FAST_BUILD)
    target_compile_options(game_code PRIVATE /Od)
else()
    target_compile_options(game_code PRIVATE /O1)
endif()

set(RUNTIME_FILES
    arm_ops.c
    audio/bcstm.cpp audio/dsp_hle.cpp
    dump.cpp frontend/sdl.cpp frontend/settings.cpp
    hle/apt.cpp hle/cecd.cpp hle/cfg.cpp hle/dsp.cpp hle/err.cpp hle/frd.cpp hle/fs.cpp
    hle/gsp.cpp hle/hid.cpp hle/offline.cpp hle/ptm.cpp hle/service.cpp hle/srv.cpp
    hle/stubs.cpp hle/uds.cpp hle/y2r.cpp
    kernel/kernel.cpp kernel/svc.cpp
    level5.cpp loader.cpp log.cpp memory.cpp mods.cpp net/air.cpp net/relay.cpp platform.cpp
    video/gpu/gpu.cpp video/lighting.cpp video/pica.cpp video/raster.cpp video/shader.cpp
    video/texture.cpp video/transfer.cpp video/upscale.cpp video/widescreen.cpp
)
list(TRANSFORM RUNTIME_FILES PREPEND "${RUNTIME}/src/")

add_executable(NewSuperMarioBros2 src/main.cpp src/shared_font.cpp src/save_storage.cpp src/pica_shader_jit.cpp ${RUNTIME_FILES})
target_include_directories(NewSuperMarioBros2 PRIVATE "${RUNTIME}/include" "${RUNTIME}/src" src "${UPSTREAM}/xbyak-df112862583c2d327c1d9782fd28f53aa675f11d")
target_compile_definitions(NewSuperMarioBros2 PRIVATE NOMINMAX _CRT_SECURE_NO_WARNINGS)
target_compile_options(NewSuperMarioBros2 PRIVATE /W3 /utf-8)
target_link_libraries(NewSuperMarioBros2 PRIVATE game_code SDL3::SDL3 ws2_32 bcrypt)
add_custom_command(TARGET NewSuperMarioBros2 POST_BUILD
    COMMAND "${CMAKE_COMMAND}" -E copy_if_different "$<TARGET_FILE:SDL3::SDL3>" "$<TARGET_FILE_DIR:NewSuperMarioBros2>"
)

enable_testing()
add_test(NAME cartridge_integrity
    COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tools/verify_extraction.py"
            "${CMAKE_CURRENT_SOURCE_DIR}/extracted/NSMB2-EUR.cxi")



add_test(NAME native_startup_routine
    COMMAND NewSuperMarioBros2 --verify-startup "${CMAKE_CURRENT_SOURCE_DIR}/extracted/NSMB2-EUR.cxi")

set(DXC "${UPSTREAM}/dxc-1.8.2505.1/bin/x64/dxc.exe")
if(NOT EXISTS "${DXC}")
    message(FATAL_ERROR "Prepare the pinned shader compiler with scripts/prepare.ps1")
endif()
set(LCD_HEADER "${CMAKE_CURRENT_BINARY_DIR}/nsmb2_lcd.inc")
add_custom_command(
    OUTPUT "${LCD_HEADER}"
    COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tools/compile_lcd.py"
            "${DXC}" "${CMAKE_CURRENT_SOURCE_DIR}/src/lcd_blit.hlsl" "${LCD_HEADER}"
    DEPENDS tools/compile_lcd.py src/lcd_blit.hlsl "${DXC}"
    VERBATIM
)
target_sources(NewSuperMarioBros2 PRIVATE "${LCD_HEADER}")
target_include_directories(NewSuperMarioBros2 PRIVATE "${CMAKE_CURRENT_BINARY_DIR}")




add_test(NAME etc1a4_texture_updates COMMAND NewSuperMarioBros2 --verify-textures)
add_test(NAME native_display_colors COMMAND NewSuperMarioBros2 --verify-display-colors)
