# Aeropendulo firmware - NUCLEO-L476RG
# Build:  cmake -B build -G Ninja -DCMAKE_TOOLCHAIN_FILE=cmake/arm-none-eabi.cmake
#         cmake --build build
# Output: build/aeropendulo.bin (drag it onto the NOD_L476RG drive to flash)
cmake_minimum_required(VERSION 3.20)
project(aeropendulo C ASM)

set(CMAKE_C_STANDARD 11)
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Debug)
endif()

set(MCU_FLAGS -mcpu=cortex-m4 -mthumb -mfpu=fpv4-sp-d16 -mfloat-abi=hard)

file(GLOB APP_SOURCES Core/Src/*.c)
file(GLOB HAL_SOURCES Drivers/HAL/Src/*.c)

add_executable(${PROJECT_NAME}.elf
  ${APP_SOURCES}
  ${HAL_SOURCES}
  Startup/startup_stm32l476xx.s
)

target_include_directories(${PROJECT_NAME}.elf PRIVATE
  Core/Inc
  Drivers/HAL/Inc
  Drivers/CMSIS/Device
  Drivers/CMSIS/Include
)

target_compile_definitions(${PROJECT_NAME}.elf PRIVATE STM32L476xx USE_HAL_DRIVER)

target_compile_options(${PROJECT_NAME}.elf PRIVATE
  ${MCU_FLAGS} -Wall -ffunction-sections -fdata-sections
  $<$<CONFIG:Debug>:-Og -g3>
  $<$<CONFIG:Release>:-O2>
)

target_link_options(${PROJECT_NAME}.elf PRIVATE
  ${MCU_FLAGS}
  -T${CMAKE_SOURCE_DIR}/STM32L476RGTX_FLASH.ld
  --specs=nano.specs --specs=nosys.specs
  -u _printf_float
  -Wl,--gc-sections -Wl,--no-warn-rwx-segments -Wl,-Map=${PROJECT_NAME}.map -Wl,--print-memory-usage
)
target_link_libraries(${PROJECT_NAME}.elf PRIVATE m)

add_custom_command(TARGET ${PROJECT_NAME}.elf POST_BUILD
  COMMAND ${CMAKE_OBJCOPY} -O binary ${PROJECT_NAME}.elf ${PROJECT_NAME}.bin
  COMMAND ${CMAKE_SIZE} ${PROJECT_NAME}.elf
)
