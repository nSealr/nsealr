#include "device.h"
#include "secret_qr.h"
#include "secret_raster.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* A host simulator uses published test entropy. The P4 supplies qualified RNG. */
static uint64_t clock_ms = 1000;
static uint32_t draw_buffer[320 * 480];
static uint8_t pixels[320 * 480 * 3];
static uint16_t secret_tile[P4_SECRET_TILE_PIXELS];
static p4_secret_qr_t secret_qr;
static lv_indev_t *pointer;
static lv_point_t point;
static bool down, scanning, presenting;
static bool secrets_visible;
static const char *render_dir;
static unsigned frames, pending_action;
static bool dispatching;
static void dispatch(void);

uint64_t platform_now(void) { return clock_ms; }
void platform_wipe(void *p, size_t n) {
    volatile unsigned char *v = p;
    while (n--)
        *v++ = 0;
}
void *platform_public_alloc(size_t n) { return malloc(n); }
void platform_public_free(void *p) { free(p); }
void platform_new_context(void) {}
void platform_revoke(void) {}
_Noreturn void platform_fail(void) {
    fputs("Native owner failed closed\n", stderr);
    abort();
}
bool platform_random32(uint8_t out[32]) {
    static unsigned request;
    memset(out, 0, 32);
    out[31] = (uint8_t)request++;
    return true;
}
bool platform_scan_start(void) {
    scanning = true;
    return true;
}
bool platform_scan_stop(void) {
    scanning = false;
    return true;
}

static void flush(lv_display_t *display, const lv_area_t *area, uint8_t *data) {
    const uint32_t *p = (const uint32_t *)data;
    for (int y = area->y1; y <= area->y2; y++)
        for (int x = area->x1; x <= area->x2; x++) {
            size_t at = ((size_t)y * 320 + (size_t)x) * 3;
            uint32_t c = *p++;
            pixels[at] = (uint8_t)((((c >> 16) & 255) >> 3) * 255 / 31);
            pixels[at + 1] = (uint8_t)((((c >> 8) & 255) >> 2) * 255 / 63);
            pixels[at + 2] = (uint8_t)(((c & 255) >> 3) * 255 / 31);
        }
    lv_display_flush_ready(display);
}
static void read_pointer(lv_indev_t *unused, lv_indev_data_t *data) {
    (void)unused;
    data->point = point;
    data->state = down ? LV_INDEV_STATE_PRESSED : LV_INDEV_STATE_RELEASED;
}
static void draw(void) {
    lv_obj_update_layout(lv_screen_active());
    lv_tick_inc(40);
    clock_ms += 40;
    lv_timer_handler();
    lv_refr_now(NULL);
    dispatch();
}
static void callback(unsigned action, void *unused) {
    (void)unused;
    if (!pending_action)
        pending_action = action;
}
static void dispatch(void) {
    if (dispatching)
        return;
    dispatching = true;
    while (pending_action) {
        unsigned selected = pending_action;
        pending_action = 0;
        device_action(selected);
    }
    dispatching = false;
}
bool platform_present(const ui_view *view) {
    ui_show(view, callback, NULL);
    presenting = true;
    draw();
    presenting = false;
    lv_obj_t *reader = ui_reader();
    device_presented(reader && lv_obj_get_scroll_bottom(reader) <= 1);
    return true;
}
void platform_input_changed(size_t n) {
    ui_set_input_length(n);
    draw();
}
void platform_review_ready(void) {
    ui_enable_next();
    if (!presenting)
        draw();
}
static void tile_to_frame(unsigned y0) {
    for (unsigned y = 0; y < 16; y++)
        for (unsigned x = 0; x < 320; x++) {
            uint16_t c = secret_tile[y * 320 + x];
            size_t at = ((size_t)y0 + y) * 320 * 3 + x * 3;
            pixels[at] = (uint8_t)(((c >> 11) & 31) * 255 / 31);
            pixels[at + 1] = (uint8_t)(((c >> 5) & 63) * 255 / 63);
            pixels[at + 2] = (uint8_t)((c & 31) * 255 / 31);
        }
    platform_wipe(secret_tile, sizeof(secret_tile));
}
bool platform_secret_text(const uint8_t *p, size_t n) {
    bool lines = false;
    for (size_t i = 0; i < n; i++)
        if (p[i] == '\n')
            lines = true;
    for (unsigned row = 0; row < 12; row++) {
        bool ok = lines ? p4_secret_raster_lines(p, n, row, secret_tile, P4_SECRET_TILE_PIXELS)
                        : p4_secret_raster(p, n, row, secret_tile, P4_SECRET_TILE_PIXELS);
        if (!ok)
            return false;
        tile_to_frame(152 + row * 16);
    }
    secrets_visible = true;
    return true;
}
bool platform_secret_qr(const uint8_t *p, size_t n) {
    if (!p4_secret_qr_encode(&secret_qr, p, n))
        return false;
    for (unsigned row = 0; row < 16; row++) {
        if (!p4_secret_qr_tile(&secret_qr, row, secret_tile, P4_SECRET_TILE_PIXELS))
            return false;
        tile_to_frame(144 + row * 16);
    }
    secrets_visible = true;
    return true;
}
bool platform_secret_clear(void) {
    if (secrets_visible) {
        lv_obj_invalidate(lv_screen_active());
        draw();
    }
    secrets_visible = false;
    p4_secret_qr_clear(&secret_qr);
    platform_wipe(secret_tile, sizeof(secret_tile));
    return true;
}
static void tap(int x, int y) {
    point = (lv_point_t){.x = x, .y = y};
    down = true;
    lv_indev_read(pointer);
    lv_tick_inc(30);
    clock_ms += 30;
    down = false;
    lv_indev_read(pointer);
    dispatch();
    if (!secrets_visible)
        draw();
}
static void drag(int x, int y0, int y1) {
    point = (lv_point_t){.x = x, .y = y0};
    down = true;
    lv_indev_read(pointer);
    for (int i = 1; i <= 12; i++) {
        point.y = y0 + (y1 - y0) * i / 12;
        lv_tick_inc(30);
        clock_ms += 30;
        lv_indev_read(pointer);
    }
    down = false;
    lv_indev_read(pointer);
    for (int i = 0; i < 15; i++)
        draw();
}
static void save_frame(const char *name) {
    if (!render_dir)
        return;
    char path[2048];
    assert(snprintf(path, sizeof(path), "%s/%s.ppm", render_dir, name) < (int)sizeof(path));
    FILE *out = fopen(path, "wb");
    assert(out);
    fprintf(out, "P6\n320 480\n255\n");
    assert(fwrite(pixels, 1, sizeof(pixels), out) == sizeof(pixels));
    assert(fclose(out) == 0);
    frames++;
}
static void type(const char *value) {
    for (size_t i = 0; value[i]; i++)
        device_action((unsigned char)value[i]);
}
static const char words[] =
    "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about";
static void feed_request(const char *event) {
    char input[NS_MAX_MESSAGE];
    int n =
        snprintf(input, sizeof(input),
                 "{\"id\":\"native-flow\",\"method\":\"sign_event\",\"params\":[\"%s\"]}", event);
    assert(n > 0 && (size_t)n < sizeof(input));
    for (unsigned i = 0; i < ((unsigned)n + NS_QR_CHUNK - 1) / NS_QR_CHUNK; i++) {
        uint8_t frame[NS_MAX_FRAME];
        size_t size = 0;
        assert(ns_encode_frame((const uint8_t *)input, (size_t)n, i, frame, sizeof(frame), &size) ==
               NS_OK);
        device_scan_bytes(frame, size);
    }
}
static void flow_test(void) {
    save_frame("01-home");
    tap(140, 175);
    save_frame("02-create");
    tap(140, 175);
    tap(140, 175);
    tap(140, 175);
    assert(ns_is_loaded(device_core()) && ns_word_count(device_core()) == 12);
    save_frame("03-identity");
    uint8_t original[64], restored[64];
    size_t n = 0;
    assert(ns_public_key(device_core(), 0, original, sizeof(original), &n) == NS_OK && n == 64);
    tap(215, 442);
    save_frame("04-backup-menu");
    tap(140, 175);
    save_frame("05-backup-words");
    tap(215, 442);
    tap(215, 442);
    save_frame("06-verify-backup");
    tap(215, 442);
    assert(!ns_is_loaded(device_core()));
    tap(140, 233);
    save_frame("07-word-entry");
    type(words);
    tap(215, 442);
    tap(140, 175);
    tap(140, 175);
    assert(ns_public_key(device_core(), 0, restored, sizeof(restored), &n) == NS_OK &&
           !memcmp(original, restored, 64));
    tap(215, 442);
    save_frame("08-ready");
    tap(140, 175);
    assert(scanning);
    save_frame("09-scanner");
    tap(60, 442);
    assert(!scanning && ns_is_loaded(device_core()));
    tap(140, 175);
    char event[1024];
    int wrote =
        snprintf(event, sizeof(event),
                 "{\\\"pubkey\\\":\\\"%.*s\\\",\\\"created_at\\\":1794211200,\\\"kind\\\":1,"
                 "\\\"tags\\\":[],\\\"content\\\":\\\"Hello from an offline Nostr signer.\\\"}",
                 64, original);
    assert(wrote > 0 && (size_t)wrote < sizeof(event));
    feed_request(event);
    assert(!scanning);
    save_frame("10-review");
    uint32_t count = ns_review_count(device_core());
    assert(count > 0);
    /* Tap Next only after the actual renderer exposes the complete item. */
    for (uint32_t i = 0; i < count; i++) {
        lv_obj_t *reader = ui_reader();
        if (!reader)
            break;
        while (lv_obj_get_scroll_bottom(reader) > 1)
            drag(260, 370, 180);
        tap(215, 442);
    }
    save_frame("11-decision");
    tap(140, 175);
    ns_text result;
    assert(ns_response(device_core(), &result) == NS_OK && result.len);
    save_frame("12-response");
    if (render_dir) {
        char path[2048];
        snprintf(path, sizeof(path), "%s/signed-response.json", render_dir);
        FILE *out = fopen(path, "wb");
        assert(out);
        assert(fwrite(result.data, 1, result.len, out) == result.len);
        assert(fclose(out) == 0);
    }
    tap(60, 442);
    assert(ns_response(device_core(), &result) != NS_OK);
    tap(140, 175);
    assert(scanning);
    feed_request(event);
    tap(60, 442);
    assert(ns_response(device_core(), &result) == NS_OK);
    tap(60, 442);
    uint8_t public_test_nsec[64];
    size_t nsec_len = 0;
    assert(ns_backup(device_core(), 1, public_test_nsec, sizeof(public_test_nsec), &nsec_len) ==
           NS_OK);
    tap(270, 26);
    assert(!ns_is_loaded(device_core()));
    /* A stale UI approval cannot resurrect the prior request after lock. */
    device_action(1025);
    assert(ns_response(device_core(), &result) != NS_OK);
    /* Practical QR recovery uses the same scanner purpose as the device. */
    tap(140, 233);
    tap(140, 175);
    assert(scanning);
    device_scan_bytes(public_test_nsec, nsec_len);
    for (size_t i = 0; i < nsec_len; i++)
        assert(public_test_nsec[i] == 0);
    assert(ns_is_loaded(device_core()));
    tap(215, 442);
    tap(140, 233);
    save_frame("13-public-identity");
    tap(60, 442);

    /* A long prose item cannot advance until rendered; explicit local partial
     * approval still requires every authority field to have been presented. */
    tap(140, 175);
    char long_text[1801], long_event[4096];
    memset(long_text, 'a', sizeof(long_text) - 1);
    long_text[sizeof(long_text) - 1] = 0;
    wrote = snprintf(long_event, sizeof(long_event),
                     "{\\\"pubkey\\\":\\\"%.*s\\\",\\\"created_at\\\":1794211200,\\\"kind\\\":1,"
                     "\\\"tags\\\":[],\\\"content\\\":\\\"%s\\\"}",
                     64, original, long_text);
    assert(wrote > 0 && (size_t)wrote < sizeof(long_event));
    feed_request(long_event);
    lv_obj_t *authority = ui_reader();
    assert(authority && lv_obj_get_scroll_bottom(authority) > 1);
    tap(215, 442);
    assert(ui_reader() == authority);
    while (lv_obj_get_scroll_bottom(authority) > 1)
        drag(260, 370, 180);
    tap(215, 442);
    lv_obj_t *prose = ui_reader();
    assert(prose && lv_obj_get_scroll_bottom(prose) > 1);
    tap(215, 442);
    assert(ui_reader() == prose);
    save_frame("14-long-prose");
    tap(258, 122);
    assert(!ui_reader());
    tap(140, 175);
    save_frame("15-partial-consent");
    assert(ns_response(device_core(), &result) != NS_OK);
    tap(215, 442);
    assert(ns_response(device_core(), &result) == NS_OK);
    tap(60, 442);
    tap(270, 26);
    assert(!ns_is_loaded(device_core()));

    char escaped[80];
    size_t escaped_len = 0;
    const uint8_t tricky[] = {0x61, 0xe2, 0x80, 0xae, 0x5c, 0x62, 0x00};
    assert(ui_escape_text(tricky, sizeof(tricky), escaped, sizeof(escaped), &escaped_len));
    assert(!strcmp(escaped, "a\\u{202e}\\\\b\\u{0}"));
    const uint8_t invalid[] = {0xc0, 0x80};
    assert(!ui_escape_text(invalid, sizeof(invalid), escaped, sizeof(escaped), &escaped_len));
    puts("PASS: real-core create/backup/clear/restore; QR frame collection; rendered review; sign, "
         "reject, cancel, response clear and lock");
}
int main(int argc, char **argv) {
    lv_init();
    lv_display_t *display = lv_display_create(320, 480);
    lv_display_set_color_format(display, LV_COLOR_FORMAT_XRGB8888);
    lv_display_set_buffers(display, draw_buffer, NULL, sizeof(draw_buffer),
                           LV_DISPLAY_RENDER_MODE_FULL);
    lv_display_set_flush_cb(display, flush);
    pointer = lv_indev_create();
    lv_indev_set_type(pointer, LV_INDEV_TYPE_POINTER);
    lv_indev_set_read_cb(pointer, read_pointer);
    assert(device_init());
    if (argc == 2 && !strcmp(argv[1], "--test"))
        flow_test();
    else if (argc == 3 && !strcmp(argv[1], "--render")) {
        render_dir = argv[2];
        flow_test();
        printf("Rendered %u actual-owner screens with published test entropy\n", frames);
    } else if (argc == 3 && !strcmp(argv[1], "--interactive")) {
        char command[128];
        render_dir = NULL;
        for (;;) {
            FILE *out = fopen(argv[2], "wb");
            assert(out);
            fprintf(out, "P6\n320 480\n255\n");
            fwrite(pixels, 1, sizeof(pixels), out);
            fclose(out);
            puts("ready");
            fflush(stdout);
            if (!fgets(command, sizeof(command), stdin))
                break;
            int x, y, end;
            if (sscanf(command, "tap %d %d", &x, &y) == 2)
                tap(x, y);
            else if (sscanf(command, "drag %d %d %d", &x, &y, &end) == 3)
                drag(x, y, end);
            else if (!strcmp(command, "quit\n"))
                break;
        }
    } else {
        fprintf(stderr, "Usage: %s --test | --render DIRECTORY | --interactive FRAME.ppm\n",
                argv[0]);
        return 2;
    }
    ns_deinit(device_core());
    lv_deinit();
    return 0;
}
