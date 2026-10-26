// SPDX-License-Identifier: MIT
#include "worker_watchdog.h"
#include "p4_local.h"
#include "esp_task_wdt.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"
#include "sdkconfig.h"
#ifndef P4_WDT_PROBE_MODE
#error Explicit public-fixture probe mode required
#endif
#if !CONFIG_ESP_TASK_WDT_EN || !CONFIG_ESP_TASK_WDT_INIT || !CONFIG_ESP_TASK_WDT_PANIC || CONFIG_ESP_TASK_WDT_TIMEOUT_S != 5
#error Public P4 worker requires explicit five-second panic watchdog configuration
#endif
#if !CONFIG_ESP_SYSTEM_PANIC_SILENT_REBOOT || !CONFIG_ESP_COREDUMP_ENABLE_TO_NONE
#error Public P4 proof requires quiet reboot and no coredump
#endif
static TaskHandle_t owner;
void p4_worker_watchdog_start(void) {
    if(owner || !xTaskGetCurrentTaskHandle())p4_fatal();
    owner=xTaskGetCurrentTaskHandle();
    if(esp_task_wdt_add(owner)!=ESP_OK || esp_task_wdt_status(owner)!=ESP_OK)p4_fatal();
}
void p4_worker_idle(uint32_t delay_ms) {
    // No other task, timer, camera, DMA or decoder callback can feed this owner.
    if(!owner || xTaskGetCurrentTaskHandle()!=owner || delay_ms>250 ||
       esp_task_wdt_reset()!=ESP_OK)p4_fatal();
    vTaskDelay(pdMS_TO_TICKS(delay_ms));
}
void p4_worker_fault_probe(void) {
    if(xTaskGetCurrentTaskHandle()!=owner)p4_fatal();
#if P4_WDT_PROBE_MODE == 1
    p4_ui_status("PUBLIC WDT BUSY PROBE\nNo engine/key initialized\nExpect reset; no input");
    ESP_LOGW("p4_wdt","PUBLIC busyCPU fault; real_ms=%lld",(long long)p4_monotonic_ms());
    // Interrupts stay enabled; no feed, no second operation, no host trigger.
    for(;;) __asm__ volatile ("" ::: "memory");
#elif P4_WDT_PROBE_MODE == 2
    p4_ui_status("PUBLIC WDT WAIT PROBE\nNo engine/key initialized\nExpect reset; no input");
    SemaphoreHandle_t never=xSemaphoreCreateBinary();if(!never)p4_fatal();
    ESP_LOGW("p4_wdt","PUBLIC blockingwait fault; real_ms=%lld",(long long)p4_monotonic_ms());
    // Private empty semaphore, no producer/handle export. Idle tasks may run.
    (void)xSemaphoreTake(never,portMAX_DELAY);p4_fatal();
#elif P4_WDT_PROBE_MODE != 0
#error Unknown probe mode
#endif
}
