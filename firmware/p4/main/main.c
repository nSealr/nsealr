#include "app_video.h"
#include "board.h"
#include "board_power.h"
#include "board_radio.h"
#include "board_rng.h"
#include "board_rng_logic.h"
#include "bsp/display.h"
#include "bsp/esp-bsp.h"
#include "bsp/touch.h"
#include "device.h"
#include "display_ack.h"
#include "driver/gpio.h"
#include "esp_attr.h"
#include "esp_cache.h"
#include "esp_heap_caps.h"
#include "esp_lcd_panel_ops.h"
#include "esp_log.h"
#include "esp_lv_adapter.h"
#include "esp_lv_adapter_display.h"
#include "esp_lv_adapter_input.h"
#include "esp_memory_utils.h"
#include "esp_private/esp_cache_private.h"
#include "esp_system.h"
#include "esp_task_wdt.h"
#include "esp_timer.h"
#include "frame_pixels.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "freertos/task.h"
#include "photo_capture.h"
#include "power_status.h"
#include "quirc.h"
#include "secret_qr.h"
#include "secret_raster.h"
#include "src/misc/cache/instance/lv_image_cache.h"
#include <stdatomic.h>
#include <string.h>

static TaskHandle_t owner_task;
static lv_display_t *display;
static esp_lcd_panel_handle_t panel;
static SemaphoreHandle_t draw_done, camera_owned, camera_copied, camera_ready;
static p4_display_ack_t ack;
static portMUX_TYPE ack_lock = portMUX_INITIALIZER_UNLOCKED;
static atomic_bool fault, revoked, navigation, direct, camera_active;
static atomic_uint epoch = 1, action;
static uint32_t render_generation;
static uint64_t released_at;
static _Alignas(64) DRAM_ATTR uint16_t secret_tile[P4_SECRET_TILE_PIXELS];
static DRAM_ATTR p4_secret_qr_t secret_qr;
static DRAM_ATTR p4_photo_capture photo;
typedef struct allocation {
    struct allocation *next, *previous;
    void *base, *payload;
    size_t size;
} allocation;
static allocation *allocations;
static uint32_t random_operation;
static bool secret_visible;
static int video = -1;
static void *camera_buffers[2];
static struct quirc *decoder;
static struct quirc_code *qr_code;
static struct quirc_data *qr_data;
static const uint8_t *camera_rgb;
static size_t camera_length;
static uint16_t *camera_preview;
static lv_image_dsc_t camera_image;
static uint64_t preview_at;
static uint64_t camera_frame_at;
static lv_obj_t *camera_widget;
static bool photo_mode, photo_frozen;
static bool camera_owner_held, camera_callback_waiting;
static unsigned brightness = 100;
static bool preview_attach(void);
static bool camera_stop(bool keep_preview);

_Static_assert((unsigned)DEVICE_POWER_BATTERY == (unsigned)P4_POWER_BATTERY &&
                   (unsigned)DEVICE_POWER_EXTERNAL == (unsigned)P4_POWER_EXTERNAL &&
                   (unsigned)DEVICE_POWER_UNKNOWN == (unsigned)P4_POWER_UNKNOWN,
               "Power state ABI");
unsigned platform_power_state(void) { return board_power_state(); }
bool platform_display_brightness(unsigned percent) {
    if (percent < 20 || percent > 100 || bsp_display_brightness_set((int)percent) != ESP_OK)
        return false;
    brightness = percent;
    return true;
}
static esp_err_t backlight_on(void) { return bsp_display_brightness_set((int)brightness); }

uint32_t board_epoch(void) { return atomic_load(&epoch); }
bool board_revoked(void) { return atomic_load(&revoked) || atomic_load(&fault); }
uint64_t IRAM_ATTR platform_now(void) { return (uint64_t)(esp_timer_get_time() / 1000); }
void platform_wipe(void *ptr, size_t n) {
    volatile uint8_t *p = ptr;
    while (n--)
        *p++ = 0;
}
void platform_revoke(void) {
    atomic_store(&revoked, true);
    atomic_fetch_add(&epoch, 1);
}
void platform_new_context(void) {
    if (atomic_load(&fault))
        platform_fail();
    if (xTaskGetCurrentTaskHandle() == owner_task)
        board_rng_retire();
    if (atomic_fetch_add(&epoch, 1) == UINT32_MAX)
        platform_fail();
    atomic_store(&revoked, false);
}
void *platform_public_alloc(size_t n) {
    return heap_caps_malloc(n, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
}
void platform_public_free(void *p) { heap_caps_free(p); }
void *ns_platform_alloc(size_t size, size_t align) {
    if (xTaskGetCurrentTaskHandle() != owner_task || board_revoked() || !size)
        return NULL;
    if (align < sizeof(void *))
        align = sizeof(void *);
    if ((align & (align - 1)) || size > SIZE_MAX - sizeof(allocation) - align)
        return NULL;
    void *base = heap_caps_malloc(size + sizeof(allocation) + align - 1,
                                  MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT);
    if (!base)
        return NULL;
    uintptr_t address =
        ((uintptr_t)base + sizeof(allocation) + align - 1) & ~(uintptr_t)(align - 1);
    allocation *entry = (allocation *)(address - sizeof(allocation));
    *entry =
        (allocation){.next = allocations, .base = base, .payload = (void *)address, .size = size};
    if (allocations)
        allocations->previous = entry;
    allocations = entry;
    return (void *)address;
}
void ns_platform_free(void *p, size_t size, size_t align) {
    (void)align;
    if (!p)
        return;
    allocation *entry = (allocation *)((uint8_t *)p - sizeof(allocation));
    if (entry->payload != p || entry->size != size)
        platform_fail();
    if (entry->previous)
        entry->previous->next = entry->next;
    else
        allocations = entry->next;
    if (entry->next)
        entry->next->previous = entry->previous;
    void *base = entry->base;
    platform_wipe(p, size);
    platform_wipe(entry, sizeof(*entry));
    heap_caps_free(base);
}
_Noreturn void ns_platform_abort(void) { platform_fail(); }
_Noreturn void platform_fail(void) {
    atomic_store(&fault, true);
    atomic_store(&navigation, false);
    atomic_store(&revoked, true);
    (void)bsp_display_backlight_off();
    board_radio_before_abort();
    /* All core calls and their fatal paths run on this sole owner task. Other
     * tasks only latch a fault; they never race a key teardown. */
    if (xTaskGetCurrentTaskHandle() == owner_task) {
        p4_photo_clear(&photo);
        photo_mode = photo_frozen = false;
        /* Bounded, nonrecursive cleanup. A failed join leaves DMA buffers alone;
         * restart is mandatory and is not a claim of verified memory erasure. */
        (void)camera_stop(false);
        device_emergency_clear();
        for (allocation *entry = allocations; entry; entry = entry->next)
            platform_wipe(entry->payload, entry->size);
        platform_wipe(secret_tile, sizeof(secret_tile));
        platform_wipe(&secret_qr, sizeof(secret_qr));
    }
    esp_restart();
    for (;;) {
    }
}
static bool IRAM_ATTR color_done(esp_lcd_panel_io_handle_t io, esp_lcd_panel_io_event_data_t *event,
                                 void *context) {
    (void)io;
    (void)event;
    (void)context;
    bool adapter_yield =
        !atomic_load(&direct) && esp_lv_adapter_display_notify_color_trans_done_from_isr(display);
    BaseType_t wake = pdFALSE;
    portENTER_CRITICAL_ISR(&ack_lock);
    bool ok = p4_display_ack_complete(&ack, render_generation, ack.pending_serial, platform_now());
    portEXIT_CRITICAL_ISR(&ack_lock);
    if (!ok)
        atomic_store(&fault, true);
    xSemaphoreGiveFromISR(draw_done, &wake);
    return adapter_yield || wake == pdTRUE;
}
static esp_err_t draw_bitmap(lv_display_t *d, esp_lcd_panel_handle_t p, int x0, int y0, int x1,
                             int y1, const void *pixels, void *unused) {
    (void)unused;
    if (d != display || atomic_load(&fault))
        return ESP_ERR_INVALID_STATE;
    if (xSemaphoreTake(draw_done, 0) == pdTRUE) {
        atomic_store(&fault, true);
        return ESP_ERR_INVALID_STATE;
    }
    uint32_t serial;
    portENTER_CRITICAL(&ack_lock);
    bool ok = p4_display_ack_submit(&ack, render_generation, platform_now(), &serial);
    uint64_t end = ack.deadline;
    portEXIT_CRITICAL(&ack_lock);
    if (!ok) {
        atomic_store(&fault, true);
        return ESP_ERR_INVALID_STATE;
    }
    esp_err_t status = esp_lcd_panel_draw_bitmap(p, x0, y0, x1, y1, pixels);
    uint64_t now = platform_now();
    if (status != ESP_OK || now >= end ||
        xSemaphoreTake(draw_done, pdMS_TO_TICKS((uint32_t)(end - now))) != pdTRUE) {
        atomic_store(&fault, true);
        return ESP_ERR_TIMEOUT;
    }
    portENTER_CRITICAL(&ack_lock);
    ok = p4_display_ack_collected(&ack, render_generation, serial, platform_now());
    portEXIT_CRITICAL(&ack_lock);
    if (!ok)
        atomic_store(&fault, true);
    return ok ? ESP_OK : ESP_ERR_TIMEOUT;
}
static bool begin_draw(void) {
    render_generation++;
    portENTER_CRITICAL(&ack_lock);
    bool ok = p4_display_ack_begin(&ack, render_generation, platform_now());
    portEXIT_CRITICAL(&ack_lock);
    return ok;
}
static bool end_draw(bool allow_unchanged) {
    portENTER_CRITICAL(&ack_lock);
    bool ok = allow_unchanged && !ack.sent
                  ? p4_display_ack_abandon(&ack, render_generation)
                  : p4_display_ack_finish(&ack, render_generation, platform_now());
    portEXIT_CRITICAL(&ack_lock);
    return ok && !atomic_load(&fault);
}
static void queue_action(unsigned selected, void *unused) {
    (void)unused;
    if (!atomic_exchange(&navigation, false))
        return;
    atomic_store(&action, selected);
}
static bool refresh(bool invalidate) {
    if (secret_visible)
        return true;
    if (esp_lv_adapter_lock(1000) != ESP_OK)
        return false;
    if (!begin_draw() || esp_lv_adapter_set_dummy_draw(display, false) != ESP_OK) {
        esp_lv_adapter_unlock();
        return false;
    }
    if (invalidate)
        lv_obj_invalidate(lv_screen_active());
    /* Keep the recursive lock across the entire acknowledged frame. The LVGL
     * timer task must not start a second refresh between these operations. */
    bool ok = esp_lv_adapter_refresh_now(display) == ESP_OK;
    if (esp_lv_adapter_set_dummy_draw(display, true) != ESP_OK)
        ok = false;
    if (!end_draw(!invalidate))
        ok = false;
    esp_lv_adapter_unlock();
    return ok;
}
bool platform_present(const ui_view *v) {
    atomic_store(&navigation, false);
    atomic_store(&action, 0);
    released_at = platform_now();
    if (!board_radio_check(NULL) || esp_lv_adapter_lock(1000) != ESP_OK)
        return false;
    ui_show(v, queue_action, NULL);
    camera_widget = NULL;
    esp_lv_adapter_unlock();
    if (photo_frozen && !preview_attach())
        return false;
    if (!refresh(true) || backlight_on() != ESP_OK)
        return false;
    if (esp_lv_adapter_lock(1000) != ESP_OK)
        return false;
    lv_obj_t *reader = ui_reader();
    bool at_end = reader && lv_obj_get_scroll_bottom(reader) <= 1;
    esp_lv_adapter_unlock();
    device_presented(at_end);
    return true;
}
void platform_review_ready(void) {
    if (esp_lv_adapter_lock(1000) != ESP_OK)
        platform_fail();
    ui_enable_next();
    esp_lv_adapter_unlock();
    if (!refresh(false))
        platform_fail();
}
static bool secret_draw(const uint8_t *bytes, size_t len, bool qr, bool blank, bool region,
                        unsigned column, unsigned block_row) {
    atomic_store(&navigation, false);
    atomic_store(&action, 0);
    released_at = platform_now();
    if (bsp_display_backlight_off() != ESP_OK || esp_lv_adapter_lock(1000) != ESP_OK)
        return false;
    if (!begin_draw() || esp_lv_adapter_set_dummy_draw(display, true) != ESP_OK) {
        esp_lv_adapter_unlock();
        return false;
    }
    atomic_store(&direct, true);
    unsigned rows = blank ? 30 : qr ? 16 : 12;
    bool lines = false;
    for (size_t i = 0; i < len; i++)
        if (bytes[i] == '\n')
            lines = true;
    for (unsigned row = 0; row < rows; row++) {
        bool rendered;
        if (blank) {
            for (size_t i = 0; i < P4_SECRET_TILE_PIXELS; i++)
                secret_tile[i] = 0x0021;
            rendered = true;
        } else if (region)
            rendered = p4_secret_qr_region_tile(&secret_qr, column, block_row, row, secret_tile,
                                                P4_SECRET_TILE_PIXELS);
        else if (qr)
            rendered = p4_secret_qr_tile(&secret_qr, row, secret_tile, P4_SECRET_TILE_PIXELS);
        else if (lines)
            rendered = p4_secret_raster_lines(bytes, len, row, secret_tile, P4_SECRET_TILE_PIXELS);
        else
            rendered = p4_secret_raster(bytes, len, row, secret_tile, P4_SECRET_TILE_PIXELS);
        unsigned y = blank ? row * 16 : qr ? 148 + row * 16 : 152 + row * 16;
        if (!rendered ||
            draw_bitmap(display, panel, 0, (int)y, 320, (int)y + 16, secret_tile, NULL) != ESP_OK) {
            esp_lv_adapter_unlock();
            return false;
        }
        platform_wipe(secret_tile, sizeof(secret_tile));
    }
    bool ok = end_draw(false);
    atomic_store(&direct, false);
    esp_lv_adapter_unlock();
    secret_visible = !blank;
    if (!ok)
        return false;
    return blank || backlight_on() == ESP_OK;
}
static bool secret_lines(const ns_text *lines, const uint16_t *y, size_t count, bool keyboard,
                         uint32_t valid) {
    if (!lines || !y || count > 8)
        return false;
    atomic_store(&navigation, false);
    atomic_store(&action, 0);
    released_at = platform_now();
    if (bsp_display_backlight_off() != ESP_OK || esp_lv_adapter_lock(1000) != ESP_OK)
        return false;
    if (!begin_draw() || esp_lv_adapter_set_dummy_draw(display, true) != ESP_OK) {
        esp_lv_adapter_unlock();
        return false;
    }
    atomic_store(&direct, true);
    bool ok = true;
    for (size_t i = 0; i < count && ok; i++) {
        if (lines[i].len > 13 || y[i] < 96 || y[i] > 368) {
            ok = false;
            break;
        }
        for (unsigned row = 0; row < 2; row++) {
            if (!p4_secret_raster(lines[i].data, lines[i].len, row, secret_tile,
                                  P4_SECRET_TILE_PIXELS)) {
                ok = false;
                break;
            }
            for (unsigned r = 0; r < 16; r++)
                memmove(secret_tile + r * 208, secret_tile + r * 320 + 32, 208 * sizeof(uint16_t));
            if (draw_bitmap(display, panel, 32, y[i] + row * 16, 240, y[i] + row * 16 + 16,
                            secret_tile, NULL) != ESP_OK) {
                ok = false;
                break;
            }
            platform_wipe(secret_tile, sizeof(secret_tile));
        }
    }
    if (keyboard && ok) {
        for (unsigned row = 0; row < 10; row++) {
            if (!p4_word_keyboard_tile(valid, row, secret_tile, P4_SECRET_TILE_PIXELS) ||
                draw_bitmap(display, panel, 0, 244 + row * 16, 320, 260 + row * 16, secret_tile,
                            NULL) != ESP_OK) {
                ok = false;
                break;
            }
            platform_wipe(secret_tile, sizeof(secret_tile));
        }
    }
    if (!end_draw(false))
        ok = false;
    atomic_store(&direct, false);
    esp_lv_adapter_unlock();
    secret_visible = true;
    return ok && backlight_on() == ESP_OK;
}
bool platform_secret_lines(const ns_text *lines, const uint16_t *y, size_t count) {
    return secret_lines(lines, y, count, false, 0);
}
bool platform_word_entry(const ns_text *lines, const uint16_t *y, size_t count, uint32_t valid) {
    return secret_lines(lines, y, count, true, valid);
}
bool platform_secret_text(const uint8_t *p, size_t n) {
    return secret_draw(p, n, false, false, false, 0, 0);
}
bool platform_secret_qr(const uint8_t *p, size_t n) {
    bool ok =
        p4_secret_qr_encode(&secret_qr, p, n) && secret_draw(NULL, 0, true, false, false, 0, 0);
    p4_secret_qr_clear(&secret_qr);
    return ok;
}
bool platform_secret_qr_size(const uint8_t *p, size_t n, uint32_t *modules) {
    if (!modules)
        return false;
    *modules = 0;
    bool ok = p4_secret_qr_encode(&secret_qr, p, n);
    if (ok)
        *modules = secret_qr.modules;
    p4_secret_qr_clear(&secret_qr);
    return ok;
}
bool platform_secret_qr_region(const uint8_t *p, size_t n, unsigned column, unsigned row) {
    bool ok = p4_secret_qr_encode(&secret_qr, p, n) && column < (secret_qr.modules + 4) / 5 &&
              row < (secret_qr.modules + 4) / 5 &&
              secret_draw(NULL, 0, true, false, true, column, row);
    p4_secret_qr_clear(&secret_qr);
    return ok;
}
bool platform_secret_clear(void) {
    bool ok = !secret_visible || secret_draw(NULL, 0, false, true, false, 0, 0);
    p4_secret_qr_clear(&secret_qr);
    platform_wipe(secret_tile, sizeof(secret_tile));
    return ok;
}
bool platform_random32(uint8_t out[32]) {
    if (board_rng_begin(BOARD_ENTROPY_AUX, board_epoch(), ++random_operation) != P4_RNG_OK)
        return false;
    bool ok = board_rng_fill32(out, 32) == 32;
    int ended = board_rng_end();
    if (!ok || ended != P4_RNG_OK)
        platform_wipe(out, 32);
    return ok && ended == P4_RNG_OK;
}
static void camera_frame(uint8_t *rgb, uint8_t index, uint32_t width, uint32_t height,
                         size_t length, void *context) {
    (void)index;
    (void)context;
    if (!atomic_load(&camera_active) || xSemaphoreTake(camera_owned, 0) != pdTRUE)
        return;
    if (!atomic_load(&camera_active)) {
        xSemaphoreGive(camera_owned);
        return;
    }
    if (width != 800 || height != 800 || length != 1280000) {
        atomic_store(&fault, true);
        xSemaphoreGive(camera_owned);
        return;
    }
    camera_rgb = rgb;
    camera_length = length;
    xSemaphoreGive(camera_ready);
    if (xSemaphoreTake(camera_copied, pdMS_TO_TICKS(3000)) != pdTRUE)
        atomic_store(&fault, true);
}
static bool preview_attach(void) {
    if (esp_lv_adapter_lock(1000) != ESP_OK)
        return false;
    if (!camera_widget) {
        camera_widget = lv_image_create(lv_screen_active());
        lv_obj_set_pos(camera_widget, 32, 166);
    }
    lv_image_cache_drop(&camera_image);
    lv_image_set_src(camera_widget, &camera_image);
    lv_obj_invalidate(camera_widget);
    esp_lv_adapter_unlock();
    return true;
}
static bool wipe_camera_pixels(void *pixels, size_t length) {
    if (!pixels)
        return true;
    platform_wipe(pixels, length);
    return esp_cache_msync(pixels, length, ESP_CACHE_MSYNC_FLAG_DIR_C2M) == ESP_OK;
}
static void camera_copy_done(void) {
    camera_rgb = NULL;
    camera_length = 0;
    if (camera_callback_waiting) {
        camera_callback_waiting = false;
        xSemaphoreGive(camera_copied);
    }
}
static void camera_owner_release(void) {
    camera_copy_done();
    camera_owner_held = false;
    xSemaphoreGive(camera_owned);
}
static bool camera_stop(bool keep_preview) {
    atomic_store(&camera_active, false);
    bool ok = true, own = false;
    if (video >= 0) {
        /* Fatal cleanup may interrupt processing after ready was consumed. */
        if (camera_owner_held) {
            camera_copy_done();
            camera_owner_held = false;
            own = true;
        }
        uint64_t end = platform_now() + 1000;
        while (!own && !(own = xSemaphoreTake(camera_owned, 0) == pdTRUE)) {
            if (xSemaphoreTake(camera_ready, pdMS_TO_TICKS(10)) == pdTRUE) {
                camera_rgb = NULL;
                xSemaphoreGive(camera_copied);
                own = true;
                break;
            }
            if (platform_now() >= end) {
                atomic_store(&fault, true);
                return false;
            }
        }
        esp_err_t stopped = app_video_stream_task_stop(video);
        ok = (stopped == ESP_OK || stopped == ESP_ERR_INVALID_STATE) &&
             app_video_wait_video_stop() == ESP_OK;
        /* Never wipe a buffer while the camera may still own its DMA writes. */
        if (ok) {
            if (decoder) {
                quirc_destroy(decoder);
                decoder = NULL;
            }
            if (qr_code)
                platform_wipe(qr_code, sizeof(*qr_code));
            if (qr_data)
                platform_wipe(qr_data, sizeof(*qr_data));
            for (unsigned i = 0; i < 2; i++)
                if (!wipe_camera_pixels(camera_buffers[i], P4_PHOTO_FRAME_BYTES))
                    ok = false;
        }
        camera_rgb = NULL;
        camera_length = 0;
        if (own)
            xSemaphoreGive(camera_owned);
    }
    if (!keep_preview) {
        photo_frozen = false;
        if (display && esp_lv_adapter_lock(1000) == ESP_OK) {
            lv_image_cache_drop(&camera_image);
            if (camera_widget) {
                lv_obj_delete(camera_widget);
                camera_widget = NULL;
            }
            if (!wipe_camera_pixels(camera_preview, 256 * 192 * 2))
                ok = false;
            esp_lv_adapter_unlock();
            if (!atomic_load(&fault) && !refresh(true))
                ok = false;
        } else if (display)
            ok = false;
    }
    if (!ok)
        atomic_store(&fault, true);
    return ok;
}
bool platform_scan_start(void) {
    if (video < 0 || decoder || photo_mode || atomic_load(&camera_active))
        return false;
    decoder = quirc_new();
    if (!decoder)
        return false;
    if (quirc_resize(decoder, 800, 800) != 0) {
        quirc_destroy(decoder);
        decoder = NULL;
        return false;
    }
    if (app_video_stream_task_restart(video) != ESP_OK) {
        if (!camera_stop(false))
            platform_fail();
        return false;
    }
    preview_at = 0;
    camera_frame_at = platform_now();
    atomic_store(&camera_active, true);
    return true;
}
bool platform_scan_stop(void) {
    p4_photo_clear(&photo);
    photo_mode = false;
    return camera_stop(false);
}
bool platform_photo_start(void) {
    if (video < 0 || decoder || photo_mode || atomic_load(&camera_active))
        return false;
    p4_photo_begin(&photo);
    if (app_video_stream_task_restart(video) != ESP_OK) {
        p4_photo_clear(&photo);
        if (!camera_stop(false))
            platform_fail();
        return false;
    }
    photo_mode = true;
    photo_frozen = false;
    preview_at = 0;
    camera_frame_at = platform_now();
    atomic_store(&camera_active, true);
    return true;
}
bool platform_photo_stop(void) {
    p4_photo_clear(&photo);
    photo_mode = false;
    return camera_stop(false);
}
/* The callback retains the dequeued buffer until this owner releases copied.
 * The complete RGB565 frame is hashed; the small crop is display-only. */
static bool photo_frame(bool final) {
    camera_frame_at = platform_now();
    bool accepted = p4_photo_add(&photo, camera_rgb, camera_length, final);
    if (!photo.active)
        platform_fail();
    for (unsigned y = 0; y < 192; y++)
        for (unsigned x = 0; x < 256; x++) {
            size_t offset = ((100 + y * 25 / 8) * 800 + x * 25 / 8) * 2;
            camera_preview[y * 256 + x] =
                (uint16_t)(camera_rgb[offset] | (camera_rgb[offset + 1] << 8));
        }
    camera_owner_release();
    if (!preview_attach() || !refresh(false))
        platform_fail();
    return accepted;
}
bool platform_photo_capture(void) {
    if (!photo_mode || !atomic_load(&camera_active) || photo.frames < 4 || photo.captured)
        return false;
    /* Both queued buffers may predate the shutter. Consume two completions,
     * then accept a new final frame. No cached preview can become the final. */
    uint64_t end = platform_now() + 1800;
    for (unsigned frame = 0; frame < 3; frame++) {
        uint64_t now = platform_now();
        if (now >= end ||
            xSemaphoreTake(camera_ready, pdMS_TO_TICKS((uint32_t)(end - now))) != pdTRUE)
            return false;
        camera_owner_held = camera_callback_waiting = true;
        if (!camera_rgb || camera_length != P4_PHOTO_FRAME_BYTES)
            platform_fail();
        bool accepted = photo_frame(frame == 2);
        if (frame == 2 && !accepted)
            return false;
    }
    if (!camera_stop(true))
        platform_fail();
    photo_frozen = true;
    return true;
}
bool platform_photo_take(uint8_t digest[32]) {
    if (!digest)
        return false;
    platform_wipe(digest, 32);
    uint8_t accepted[32] = {0};
    bool ok = photo_mode && photo_frozen && p4_photo_take(&photo, accepted);
    if (!platform_photo_stop())
        ok = false;
    if (ok)
        memcpy(digest, accepted, 32);
    platform_wipe(accepted, sizeof(accepted));
    return ok;
}
static void process_camera(void) {
    if (xSemaphoreTake(camera_ready, 0) != pdTRUE)
        return;
    camera_owner_held = camera_callback_waiting = true;
    if (!camera_rgb)
        platform_fail();
    camera_frame_at = platform_now();
    if (photo_mode) {
        (void)photo_frame(false);
        return;
    }
    if (!decoder)
        platform_fail();
    int w, h;
    uint8_t *gray = quirc_begin(decoder, &w, &h);
    bool good = w == 800 && h == 800 &&
                p4_frame_gray_raw(camera_rgb, camera_length, 800, 800, gray, 640000);
    camera_copy_done();
    if (!good)
        platform_fail();
    if (platform_now() - preview_at > 150) {
        for (unsigned y = 0; y < 192; y++)
            for (unsigned x = 0; x < 256; x++) {
                unsigned g = gray[(100 + y * 25 / 8) * 800 + x * 25 / 8];
                camera_preview[y * 256 + x] =
                    (uint16_t)(((g >> 3) << 11) | ((g >> 2) << 5) | (g >> 3));
            }
        if (!preview_attach() || !refresh(false))
            platform_fail();
        preview_at = platform_now();
    }
    quirc_end(decoder);
    int count = quirc_count(decoder);
    int length = 0;
    if (count == 1) {
        quirc_extract(decoder, 0, qr_code);
        quirc_decode_error_t result = quirc_decode(qr_code, qr_data);
        if (result == QUIRC_ERROR_DATA_ECC) {
            quirc_flip(qr_code);
            result = quirc_decode(qr_code, qr_data);
        }
        if (result == QUIRC_SUCCESS && qr_data->payload_len > 0 &&
            qr_data->payload_len <= NS_MAX_FRAME)
            length = qr_data->payload_len;
    }
    uint8_t payload[NS_MAX_FRAME];
    if (length)
        memcpy(payload, qr_data->payload, (size_t)length);
    platform_wipe(qr_code, sizeof(*qr_code));
    platform_wipe(qr_data, sizeof(*qr_data));
    camera_owner_release();
    if (length)
        device_scan_bytes(payload, (size_t)length);
    platform_wipe(payload, sizeof(payload));
}
static void init_display(void) {
    esp_lv_adapter_config_t adapter = ESP_LV_ADAPTER_DEFAULT_CONFIG();
    ESP_ERROR_CHECK(esp_lv_adapter_init(&adapter));
    ESP_ERROR_CHECK(esp_lv_adapter_set_default_display_idf_callback_registration_enabled(false));
    ESP_ERROR_CHECK(bsp_display_brightness_init());
    bsp_lcd_handles_t handles;
    ESP_ERROR_CHECK(bsp_display_new_with_handles(NULL, &handles));
    panel = handles.panel;
    esp_lv_adapter_display_config_t config = {
        .panel = handles.panel,
        .panel_io = handles.io,
        .profile = {.interface = ESP_LV_ADAPTER_PANEL_IF_OTHER,
                    .rotation = ESP_LV_ADAPTER_ROTATE_0,
                    .hor_res = 320,
                    .ver_res = 480,
                    .buffer_height = 50,
                    .use_psram = false,
                    .enable_ppa_accel = false,
                    .require_double_buffer = false},
        .tear_avoid_mode = ESP_LV_ADAPTER_TEAR_AVOID_MODE_NONE};
    display = esp_lv_adapter_register_display(&config);
    if (!display)
        platform_fail();
    esp_lv_adapter_draw_bitmap_callbacks_t draw = {.custom_draw_bitmap = draw_bitmap};
    ESP_ERROR_CHECK(esp_lv_adapter_set_draw_bitmap_callbacks(display, &draw, NULL));
    esp_lcd_panel_io_callbacks_t cb = {.on_color_trans_done = color_done};
    ESP_ERROR_CHECK(esp_lcd_panel_io_register_event_callbacks(handles.io, &cb, NULL));
    ESP_ERROR_CHECK(esp_lv_adapter_set_dummy_draw(display, true));
    bsp_touch_config_t touch_config = {0};
    esp_lcd_touch_handle_t touch;
    ESP_ERROR_CHECK(bsp_touch_new(&touch_config, &touch));
    esp_lv_adapter_touch_config_t input = ESP_LV_ADAPTER_TOUCH_DEFAULT_CONFIG(display, touch);
    if (!esp_lv_adapter_register_touch(&input))
        platform_fail();
    ESP_ERROR_CHECK(esp_lv_adapter_start());
}
static void owner(void *unused) {
    (void)unused;
    owner_task = xTaskGetCurrentTaskHandle();
    if (!board_radio_begin() || !board_rng_bind_worker())
        platform_fail();
    ESP_ERROR_CHECK(esp_task_wdt_add(NULL));
    init_display();
    if (!board_power_init(bsp_i2c_get_handle()))
        platform_fail();
    ESP_ERROR_CHECK(app_video_main(bsp_i2c_get_handle()));
    video = app_video_open(ESP_VIDEO_MIPI_CSI_DEVICE_NAME, APP_VIDEO_FMT);
    if (video < 0 || app_video_get_buf_size() != 1280000)
        platform_fail();
    size_t alignment = 64;
    ESP_ERROR_CHECK(esp_cache_get_alignment(MALLOC_CAP_SPIRAM, &alignment));
    for (unsigned i = 0; i < 2; i++) {
        camera_buffers[i] =
            heap_caps_aligned_calloc(alignment, 1, 1280000, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
        if (!camera_buffers[i])
            platform_fail();
    }
    ESP_ERROR_CHECK(app_video_set_bufs(video, 2, (const void **)camera_buffers));
    ESP_ERROR_CHECK(app_video_register_frame_operation_cb(camera_frame));
    qr_code = heap_caps_calloc(1, sizeof(*qr_code), MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
    qr_data = heap_caps_calloc(1, sizeof(*qr_data), MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
    camera_preview = heap_caps_aligned_calloc(alignment, 256 * 192, sizeof(uint16_t),
                                              MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
    if (!qr_code || !qr_data || !camera_preview)
        platform_fail();
    camera_image = (lv_image_dsc_t){.header = {.magic = LV_IMAGE_HEADER_MAGIC,
                                               .cf = LV_COLOR_FORMAT_RGB565,
                                               .w = 256,
                                               .h = 192,
                                               .stride = 512},
                                    .data_size = 256 * 192 * 2,
                                    .data = (const uint8_t *)camera_preview};
    if (!device_init())
        platform_fail();
    uint64_t last_refresh = 0;
    for (;;) {
        if (atomic_load(&fault) || !board_radio_check(NULL))
            platform_fail();
        unsigned selected = atomic_exchange(&action, 0);
        if (selected) {
            if (selected == UI_READER_END && !refresh(false))
                platform_fail();
            device_action(selected);
        }
        if (atomic_load(&camera_active)) {
            if (app_video_stream_failed() || platform_now() - camera_frame_at > 3000)
                device_scan_error();
            else
                process_camera();
        }
        device_tick(platform_now());
        if (platform_now() - last_refresh > 40 && !secret_visible) {
            if (!refresh(false))
                platform_fail();
            last_refresh = platform_now();
        }
        bool released = true;
        if (esp_lv_adapter_lock(100) != ESP_OK)
            platform_fail();
        for (lv_indev_t *d = lv_indev_get_next(NULL); d; d = lv_indev_get_next(d))
            if (lv_indev_get_type(d) == LV_INDEV_TYPE_POINTER &&
                lv_indev_get_state(d) != LV_INDEV_STATE_RELEASED)
                released = false;
        esp_lv_adapter_unlock();
        if (!released)
            released_at = platform_now();
        if (platform_now() - released_at >= 40)
            atomic_store(&navigation, true);
        ESP_ERROR_CHECK(esp_task_wdt_reset());
        vTaskDelay(pdMS_TO_TICKS(10));
    }
}
void app_main(void) {
    draw_done = xSemaphoreCreateBinary();
    camera_owned = xSemaphoreCreateBinary();
    camera_copied = xSemaphoreCreateBinary();
    camera_ready = xSemaphoreCreateBinary();
    if (!draw_done || !camera_owned || !camera_copied || !camera_ready)
        platform_fail();
    xSemaphoreGive(camera_owned);
    const size_t stack_bytes = 64 * 1024;
    StackType_t *stack = heap_caps_calloc(1, stack_bytes, MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT);
    StaticTask_t *task = heap_caps_calloc(1, sizeof(*task), MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT);
    if (!stack || !task ||
        !xTaskCreateStaticPinnedToCore(owner, "nsealr", stack_bytes, NULL, 4, stack, task, 1))
        platform_fail();
}
