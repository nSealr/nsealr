idf_component_register(SRCS "main.cpp"
    INCLUDE_DIRS "." "../../s3-io-probe/include"
    REQUIRES esp_lcd driver esp_timer esp_hw_support)
set(task_core_archive "$ENV{NSEALR_S3_NATIVE_CORE_ARCHIVE}")
if(NOT EXISTS "${task_core_archive}")
    message(FATAL_ERROR "Build the admitted native Rust core archive first")
endif()
add_prebuilt_library(s3_native_core "${task_core_archive}")
target_link_libraries(${COMPONENT_LIB} PUBLIC s3_native_core)
