idf_component_register(SRCS "main.c" "app_video.c" "p4_local.c" "local_input.c" "frame_pixels.c" "decoder_alloc.c" "decode_one.c" "worker_watchdog.c" "display_ack.c" "response_lifetime.c" "scan_admission.c" "c6_probe.c" "c6_probe_logic.c" "c6_guard.c" "p4_entropy.c" "p4_entropy_logic.c"
 INCLUDE_DIRS "." "../vendor/quirc/lib"
 REQUIRES sdmmc esp_driver_sdmmc esp_video waveshare__esp32_p4_wifi6_touch_lcd_3_5 esp_driver_gpio esp_timer esp_system esp_lcd esp_lvgl_adapter bootloader_support esp_hw_support esp_hal_ana_conv)
add_library(p4_quirc STATIC ../vendor/quirc/lib/quirc.c ../vendor/quirc/lib/identify.c ../vendor/quirc/lib/decode.c ../vendor/quirc/lib/version_db.c)
target_include_directories(p4_quirc PUBLIC ../vendor/quirc/lib)
target_compile_definitions(p4_quirc PRIVATE malloc=p4_quirc_malloc calloc=p4_quirc_calloc free=p4_quirc_free)
if(NOT DEFINED RUST_LIBRARY)
 message(FATAL_ERROR "Set RUST_LIBRARY through the versioned build.py recipe")
endif()
if(NOT EXISTS "${RUST_LIBRARY}")
 message(FATAL_ERROR "Build the pinned no_std Rust staticlib before IDF configure")
endif()
target_link_libraries(${COMPONENT_LIB} PUBLIC p4_quirc "${RUST_LIBRARY}")
target_compile_definitions(${COMPONENT_LIB} PRIVATE P4_WDT_PROBE_MODE=${P4_WDT_PROBE_MODE})

set_source_files_properties(p4_entropy.c PROPERTIES COMPILE_DEFINITIONS "P4_ENTROPY_FIXED_UNAVAILABLE=${P4_ENTROPY_FIXED_UNAVAILABLE}")
