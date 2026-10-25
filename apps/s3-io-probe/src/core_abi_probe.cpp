// SPDX-License-Identifier: MIT
#ifdef NSEALR_S3_CORE_ABI
#include <Arduino.h>
#include <esp_timer.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include "core_abi_probe.h"

extern "C" int32_t nsealr_s3_abi_check(uint8_t *output, size_t capacity);

static void core_abi_task(void *) {
    uint8_t guarded[66];
    memset(guarded, 0xA5, sizeof(guarded));
    bool negative_ok = nsealr_s3_abi_check(nullptr, 64) == -1;
    const size_t bad_capacities[] = {0, 63, 65};
    for (size_t capacity : bad_capacities) {
        negative_ok = negative_ok && nsealr_s3_abi_check(guarded + 1, capacity) == -1;
    }
    for (uint8_t b : guarded) negative_ok = negative_ok && b == 0xA5;
    const int64_t start_us = esp_timer_get_time();
    const int32_t result = nsealr_s3_abi_check(guarded + 1, 64);
    const int64_t elapsed_us = esp_timer_get_time() - start_us;
    const bool guards_ok = guarded[0] == 0xA5 && guarded[65] == 0xA5;
    // These bytes are exclusively hash output and a published fixture pubkey.
    char hex[129];
    const char digits[] = "0123456789abcdef";
    for (unsigned i = 0; i < 64; ++i) {
        hex[i * 2] = digits[guarded[i + 1] >> 4];
        hex[i * 2 + 1] = digits[guarded[i + 1] & 15U];
    }
    hex[128] = 0;
    const unsigned long watermark = (unsigned long)uxTaskGetStackHighWaterMark(nullptr);
    // Repeat only the cached public result for bounded monitor attachment.
    // The Rust call runs once. No key material or authority is retransmitted.
    for (unsigned report = 0; report < 20; ++report) {
    Serial.printf("s3-core-abi-v1 rc=%ld negative=%u guards=%u elapsed_us=%lld stack_high_water_raw=%lu public_hex=%s\n",
                  (long)result, (unsigned)negative_ok, (unsigned)guards_ok,
                  (long long)elapsed_us, watermark, hex);
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
    vTaskDelete(nullptr);
}

void start_core_abi_probe() {
    // This task has its own finite stack; it is not the default Arduino loop
    // stack. Placement/peak demand and production limits remain target gates.
    const BaseType_t result = xTaskCreatePinnedToCore(core_abi_task, "s3-core-abi",
        65536, nullptr, 1, nullptr, 1);
    Serial.printf("s3-core-abi-v1 task_created=%u stack_requested=65536\n",
                  (unsigned)(result == pdPASS));
}
#endif
