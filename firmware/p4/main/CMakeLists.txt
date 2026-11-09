if(NOT DEFINED NSEALR_CORE_ROOT)
  set(NSEALR_CORE_ROOT "${CMAKE_CURRENT_LIST_DIR}/../../../..")
endif()
set(ui "${CMAKE_CURRENT_LIST_DIR}/../../ui")
file(GLOB fonts "${ui}/fonts/font_*.c")
idf_component_register(
  SRCS "main.c" "app_video.c" "board_radio.c" "board_rng.c" "board_rng_logic.c"
       "display_ack.c" "frame_pixels.c" "secret_raster.c" "secret_qr.c" "share_file.c"
       "../../device.c" "../../word_input.c" "../../backup_check.c" "${ui}/ui.c" ${fonts}
  INCLUDE_DIRS "." "../vendor/quirc/lib" "../.." "${NSEALR_CORE_ROOT}/core/nsealr-device/include"
  REQUIRES esp_video waveshare__esp32_p4_wifi6_touch_lcd_3_5 esp_driver_gpio
       esp_timer esp_system esp_lcd esp_lvgl_adapter bootloader_support esp_hw_support esp_hal_ana_conv
       fatfs sdmmc)
if(CMAKE_BUILD_EARLY_EXPANSION)
  return()
endif()
if(NOT DEFINED RUST_LIBRARY OR NOT EXISTS "${RUST_LIBRARY}")
  message(FATAL_ERROR "Build the current nsealr-device staticlib first")
endif()
target_compile_definitions(${COMPONENT_LIB} PRIVATE LV_LVGL_H_INCLUDE_SIMPLE=1)
add_library(nsealr_quirc STATIC decoder_alloc.c ../vendor/quirc/lib/quirc.c ../vendor/quirc/lib/identify.c ../vendor/quirc/lib/decode.c ../vendor/quirc/lib/version_db.c)
target_link_libraries(nsealr_quirc PRIVATE idf::heap)
target_include_directories(nsealr_quirc PUBLIC ../vendor/quirc/lib)
target_compile_options(nsealr_quirc PUBLIC "SHELL:-include ${CMAKE_CURRENT_LIST_DIR}/decoder_limits.h")
target_compile_definitions(nsealr_quirc PRIVATE malloc=p4_quirc_malloc calloc=p4_quirc_calloc free=p4_quirc_free)
target_link_libraries(${COMPONENT_LIB} PUBLIC nsealr_quirc "${RUST_LIBRARY}")
# Secret QR generation uses the reviewed wipe of both mask-history arrays.
set(original "${CMAKE_CURRENT_LIST_DIR}/../managed_components/lvgl__lvgl/src/libs/qrcode/qrcodegen.c")
set(patched "${CMAKE_BINARY_DIR}/nsealr_qrcodegen.c")
execute_process(COMMAND "${PYTHON}" "${CMAKE_CURRENT_LIST_DIR}/patch_secret_qr.py" --source "${original}" --output "${patched}" RESULT_VARIABLE result)
if(NOT result EQUAL 0)
  message(FATAL_ERROR "Secret QR encoder source differs from the reviewed input")
endif()
get_target_property(sources __idf_lvgl__lvgl SOURCES)
list(FILTER sources EXCLUDE REGEX "src/libs/qrcode/qrcodegen\\.c$")
set_property(TARGET __idf_lvgl__lvgl PROPERTY SOURCES "${sources};${patched}")
