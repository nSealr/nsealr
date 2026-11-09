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
void platform_input_changed(size_t length);
void platform_review_ready(void);
bool platform_word_entry(const ns_text *lines, const uint16_t *y, size_t count, uint32_t valid);
bool platform_secret_lines(const ns_text *lines, const uint16_t *y, size_t count);
bool platform_secret_text(const uint8_t *bytes, size_t len);
bool platform_secret_qr(const uint8_t *bytes, size_t len);
bool platform_secret_clear(void);
bool platform_random32(uint8_t out[32]);
bool platform_scan_start(void);
bool platform_scan_stop(void);
uint64_t platform_now(void);
void platform_new_context(void);
void platform_revoke(void);
void platform_wipe(void *ptr, size_t len);
void *platform_public_alloc(size_t bytes);
void platform_public_free(void *ptr);
_Noreturn void platform_fail(void);
#endif
