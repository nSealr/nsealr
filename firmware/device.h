#ifndef NSEALR_DEVICE_H
#define NSEALR_DEVICE_H
#include "nsealr.h"
#include "ui/ui.h"
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

/* One owner task calls these. UI callbacks only enqueue input on the board. */
bool device_init(void);
void device_action(unsigned action);
void device_tick(uint64_t now_ms);
void device_presented(bool reader_at_end);
void device_scan_bytes(uint8_t *bytes, size_t len);
void device_scan_error(void);
void device_emergency_clear(void);
ns_context *device_core(void);

/* Current P4/desktop integration boundary, not a device-family framework. */
bool platform_present(const ui_view *view);
void platform_review_ready(void);
bool platform_word_entry(const ns_text *lines, const uint16_t *y, size_t count, uint32_t valid);
bool platform_secret_lines(const ns_text *lines, const uint16_t *y, size_t count);
bool platform_secret_text(const uint8_t *bytes, size_t len);
bool platform_secret_qr(const uint8_t *bytes, size_t len);
bool platform_secret_clear(void);
bool platform_random32(uint8_t out[32]);
bool platform_scan_start(void);
bool platform_scan_stop(void);
/* Camera seed material stays on the device. Stop wipes captures on every exit.
 */
bool platform_photo_start(void);
bool platform_photo_capture(void);
bool platform_photo_take(uint8_t digest32[32]);
bool platform_photo_stop(void);
bool platform_secret_qr_size(const uint8_t *bytes, size_t len, uint32_t *modules);
bool platform_secret_qr_region(const uint8_t *bytes, size_t len, unsigned column, unsigned row);
bool platform_display_brightness(unsigned percent);
enum { DEVICE_POWER_BATTERY, DEVICE_POWER_EXTERNAL, DEVICE_POWER_UNKNOWN };
unsigned platform_power_state(void);
typedef enum {
    SHARE_FILE_OK,
    SHARE_FILE_UNAVAILABLE,
    SHARE_FILE_EXISTS,
    SHARE_FILE_MISSING,
    SHARE_FILE_INVALID,
    SHARE_FILE_IO
} share_file_result;
/* Explicit local actions only. No overwrite, format, auto-load or secret logs.
 */
share_file_result platform_share_save(const uint8_t *bytes, size_t len);
share_file_result platform_share_load(uint8_t *bytes, size_t capacity, size_t *written);
uint64_t platform_now(void);
void platform_new_context(void);
void platform_revoke(void);
void platform_wipe(void *ptr, size_t len);
void *platform_public_alloc(size_t bytes);
void platform_public_free(void *ptr);
_Noreturn void platform_fail(void);
#endif
