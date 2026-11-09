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
static unsigned frames, pending_action, touches;
static char visible_title[80], visible_caption[100], visible_right[40];
/* Test inspection is enabled only for the published, deterministic test vectors. */
static bool testing;
static char test_lines[8][14];
static uint8_t test_qr[NS_MAX_FRAME];
static size_t test_qr_len;

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
    out[31] = (uint8_t)++request;
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
    snprintf(visible_title, sizeof(visible_title), "%s", view->title ? view->title : "");
    snprintf(visible_caption, sizeof(visible_caption), "%s", view->subtitle ? view->subtitle : "");
    snprintf(visible_right, sizeof(visible_right), "%s",
             view->right_label ? view->right_label : "");
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
bool platform_secret_lines(const ns_text *lines, const uint16_t *y, size_t count) {
    if (testing) {
        memset(test_lines, 0, sizeof(test_lines));
        for (size_t i = 0; i < count; i++) {
            assert(lines[i].len < 14);
            memcpy(test_lines[i], lines[i].data, lines[i].len);
        }
    }
    for (size_t i = 0; i < count; i++) {
        if (lines[i].len > 13 || y[i] < 96 || y[i] > 368)
            return false;
        for (unsigned row = 0; row < 2; row++) {
            if (!p4_secret_raster(lines[i].data, lines[i].len, row, secret_tile,
                                  P4_SECRET_TILE_PIXELS))
                return false;
            for (unsigned py = 0; py < 16; py++)
                for (unsigned x = 32; x < 240; x++) {
                    uint16_t c = secret_tile[py * 320 + x];
                    size_t at = ((size_t)y[i] + row * 16 + py) * 320 * 3 + x * 3;
                    pixels[at] = (uint8_t)(((c >> 11) & 31) * 255 / 31);
                    pixels[at + 1] = (uint8_t)(((c >> 5) & 63) * 255 / 63);
                    pixels[at + 2] = (uint8_t)((c & 31) * 255 / 31);
                }
            platform_wipe(secret_tile, sizeof(secret_tile));
        }
    }
    secrets_visible = true;
    return true;
}
bool platform_word_entry(const ns_text *lines, const uint16_t *y, size_t count, uint32_t valid) {
    if (!platform_secret_lines(lines, y, count))
        return false;
    for (unsigned row = 0; row < 10; row++) {
        if (!p4_word_keyboard_tile(valid, row, secret_tile, P4_SECRET_TILE_PIXELS))
            return false;
        tile_to_frame(244 + row * 16);
    }
    return true;
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
    if (testing) {
        assert(n <= sizeof(test_qr));
        memcpy(test_qr, p, n);
        test_qr_len = n;
    }
    if (!p4_secret_qr_encode(&secret_qr, p, n))
        return false;
    for (unsigned row = 0; row < 16; row++) {
        if (!p4_secret_qr_tile(&secret_qr, row, secret_tile, P4_SECRET_TILE_PIXELS))
            return false;
        tile_to_frame(148 + row * 16);
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
    touches++;
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
static void word_prefix(const char *word) {
    for (unsigned i = 0; i < 4 && word[i]; i++) {
        unsigned index = (unsigned)(word[i] - 'a');
        assert(index < 26);
        tap(35 + (int)(index % 7) * 42, 262 + (int)(index / 7) * 39);
    }
}
static void enter_public_words(unsigned count, bool repair) {
    unsigned entry_taps = 0, extra_taps = 0;
    for (unsigned i = 0; i < count; i++) {
        if (repair && i == 1) {
            unsigned before = touches;
            tap(60, 442);
            assert(!strcmp(test_lines[0], "abandon"));
            tap(140, 162);
            extra_taps += touches - before;
        }
        unsigned before = touches;
        const char *word = i + 1 == count ? (count == 12 ? "about" : "art") : "abandon";
        if (repair && i + 1 == count)
            word = "abandon";
        word_prefix(word);
        if (i == 0)
            save_frame("07-word-prefix");
        assert(!strcmp(test_lines[1], word));
        tap(140, 162);
        entry_taps += touches - before;
    }
    assert(entry_taps <= count * 5);
    printf("PASS: %u-word recovery entry: %u pointer taps; %u extra Back/navigation checks\n",
           count, entry_taps, extra_taps);
}
static void complete_word_review(unsigned count) {
    for (unsigned i = 0; i < (count + 3) / 4; i++)
        tap(215, 442);
}
static void text_key(char value) {
    static const char keys[] = "abcdefghijklmnopqrstuvwxyz.,-@";
    const char *at = strchr(keys, value);
    assert(at);
    unsigned i = (unsigned)(at - keys);
    tap(37 + (int)(i % 6) * 49, 194 + (int)(i / 6) * 44);
}
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
    testing = true;
    save_frame("01-home");
    tap(140, 175);
    save_frame("02-create");
    tap(140, 175);
    assert(ns_is_loaded(device_core()) && ns_word_count(device_core()) == 12);
    save_frame("03-identity");
    uint8_t original[64], restored[64];
    size_t n = 0;
    assert(ns_public_key(device_core(), 0, original, sizeof(original), &n) == NS_OK && n == 64);
    tap(140, 175);
    save_frame("04-backup-words");
    tap(215, 442);
    tap(215, 442);
    save_frame("05-check-backup");
    tap(140, 175);
    for (unsigned i = 0; i < 12; i++) {
        unsigned position = 0;
        assert(sscanf(visible_title, "Choose word %u", &position) == 1);
        const char *expected = position == 12 ? "about" : "abandon";
        unsigned match = 4;
        for (unsigned j = 0; j < 4; j++)
            if (!strcmp(test_lines[j], expected))
                match = j;
        assert(match < 4);
        if (i == 0)
            save_frame("06-backup-quiz");
        tap(140, 162 + (int)match * 56);
    }
    assert(!strcmp(visible_title, "Backup checked"));
    tap(215, 442);
    tap(270, 26);
    assert(!ns_is_loaded(device_core()));
    tap(140, 233);
    tap(140, 233);
    tap(140, 175);
    enter_public_words(12, true);
    assert(!strcmp(visible_title, "Check your words"));
    save_frame("08-checksum-repair");
    tap(140, 175);
    tap(215, 442);
    tap(215, 442);
    tap(140, 330);
    tap(287, 379);
    word_prefix("about");
    tap(140, 162);
    assert(!strcmp(visible_title, "Review words"));
    tap(215, 442);
    assert(ns_is_loaded(device_core()));
    assert(ns_public_key(device_core(), 0, restored, sizeof(restored), &n) == NS_OK &&
           !memcmp(original, restored, 64));
    tap(140, 175);
    save_frame("09-ready");
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
    char first_frame[100];
    snprintf(first_frame, sizeof(first_frame), "%s", visible_caption);
    tap(215, 442);
    clock_ms += 1000;
    device_tick(clock_ms);
    assert(!strcmp(first_frame, visible_caption));
    tap(258, 122);
    assert(strcmp(first_frame, visible_caption));
    tap(215, 442);

    if (render_dir) {
        assert(ns_response(device_core(), &result) == NS_OK);
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
    /* A stale Next action cannot resurrect the prior request after lock. */
    device_action(UI_NEXT);
    assert(ns_response(device_core(), &result) != NS_OK);
    /* Practical QR recovery uses the same scanner purpose as the device. */
    tap(140, 233);
    tap(140, 175);
    assert(scanning);
    device_scan_bytes(public_test_nsec, nsec_len);
    for (size_t i = 0; i < nsec_len; i++)
        assert(public_test_nsec[i] == 0);
    assert(ns_is_loaded(device_core()));
    tap(140, 175);
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

    tap(140, 233);
    tap(140, 233);
    tap(140, 233);
    enter_public_words(24, false);
    complete_word_review(24);
    assert(ns_is_loaded(device_core()) && ns_word_count(device_core()) == 24);
    uint8_t plain24[64], with_pass[64];
    assert(ns_public_key(device_core(), 0, plain24, sizeof(plain24), &n) == NS_OK);
    tap(140, 291);
    text_key('t');
    text_key('e');
    text_key('s');
    text_key('t');
    tap(195, 147);
    tap(215, 442);
    assert(!strcmp(visible_title, "Check passphrase"));
    save_frame("16-passphrase-review");
    tap(215, 442);
    assert(ns_public_key(device_core(), 0, with_pass, sizeof(with_pass), &n) == NS_OK &&
           memcmp(plain24, with_pass, 64));
    tap(140, 291);
    for (unsigned i = 0; i < 80; i++)
        tap(195, 147);
    tap(215, 442);
    unsigned pages = 0;
    while (!strcmp(visible_right, "Next page")) {
        assert(ns_public_key(device_core(), 0, restored, sizeof(restored), &n) == NS_OK &&
               !memcmp(with_pass, restored, 64));
        if (!pages)
            save_frame("18-long-passphrase");
        tap(215, 442);
        assert(++pages < 20);
    }
    assert(pages > 1 && !strcmp(visible_right, "Use passphrase"));
    tap(215, 442);
    assert(ns_public_key(device_core(), 0, with_pass, sizeof(with_pass), &n) == NS_OK);
    tap(140, 175);
    tap(140, 291);
    tap(140, 233);
    save_frame("17-seed-qr");
    uint8_t seedqr[96];
    size_t seedqr_len = 0;
    assert(ns_backup(device_core(), 3, seedqr, sizeof(seedqr), &seedqr_len) == NS_OK);
    tap(215, 442);
    tap(140, 175);
    assert(scanning);
    uint8_t wrong_qr[96];
    memcpy(wrong_qr, seedqr, seedqr_len);
    wrong_qr[0] = wrong_qr[0] == '0' ? '1' : '0';
    device_scan_bytes(wrong_qr, seedqr_len);
    assert(!strcmp(visible_title, "Different backup"));
    assert(ns_public_key(device_core(), 0, restored, sizeof(restored), &n) == NS_OK &&
           !memcmp(with_pass, restored, 64));
    tap(215, 442);
    assert(scanning);
    device_scan_bytes(seedqr, seedqr_len);
    assert(!strcmp(visible_title, "Backup checked"));
    assert(ns_public_key(device_core(), 0, restored, sizeof(restored), &n) == NS_OK &&
           !memcmp(with_pass, restored, 64));
    tap(215, 442);
    tap(270, 26);
    assert(!ns_is_loaded(device_core()));
    testing = false;

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
/* The UI is one real participant. Two public-data core peers exercise the
 * authenticated exchange without inventing device state or approval actions. */
static _Alignas(NS_CONTEXT_ALIGN) uint8_t peer_storage[2][NS_CONTEXT_BYTES];
static ns_context *custody[3];
static char custody_keys[3][65], custody_packets[6][NS_MAX_MESSAGE];
static uint8_t custody_backups[2][NS_THRESHOLD_MAX_BACKUP];
static size_t custody_backup_len[2];
static void public_field(const char *json, const char *name, char out[65]) {
    char needle[64];
    snprintf(needle, sizeof(needle), "\"%s\":\"", name);
    const char *start = strstr(json, needle);
    assert(start);
    start += strlen(needle);
    assert(strlen(start) >= 65 && start[64] == '"');
    memcpy(out, start, 64);
    out[64] = 0;
}
static int public_key_order(const void *a, const void *b) { return strcmp(a, b); }
static void peer_approve(unsigned i) {
    uint64_t generation = ns_review_generation(custody[i]);
    for (uint32_t k = 0; k < ns_review_count(custody[i]); k++)
        assert(ns_review_seen(custody[i], generation, k) == NS_OK);
    uint8_t random[32];
    assert(platform_random32(random));
    assert(ns_approve(custody[i], generation, false, random, 32, clock_ms) == NS_OK);
}
static void finish_visible_review(void) {
    while (ui_reader()) {
        lv_obj_t *reader = ui_reader();
        while (lv_obj_get_scroll_bottom(reader) > 1)
            drag(260, 370, 180);
        tap(215, 442);
    }
    assert(!strcmp(visible_title, "Your decision"));
    tap(140, 175);
}
static void custody_feed(unsigned recipient, const uint8_t *message, size_t length) {
    unsigned count = (unsigned)((length + NS_QR_CHUNK - 1) / NS_QR_CHUNK);
    for (unsigned i = 0; i < count; i++) {
        uint8_t frame[NS_MAX_FRAME], random[32];
        size_t written;
        assert(ns_encode_frame(message, length, i, frame, sizeof(frame), &written) == NS_OK);
        if (!recipient) {
            assert(scanning);
            device_scan_bytes(frame, written);
            for (size_t j = 0; j < written; j++)
                assert(frame[j] == 0);
        } else {
            assert(platform_random32(random));
            assert(ns_threshold_receive_frame(custody[recipient], frame, written, random,
                                              clock_ms) == (i + 1 == count ? NS_OK : NS_MORE));
        }
    }
}
static unsigned custody_collect(void) {
    unsigned written = 0;
    for (unsigned i = 0; i < 3; i++) {
        unsigned count = ns_threshold_output_count(custody[i]);
        for (unsigned k = 0; k < count; k++) {
            ns_text output;
            assert(written < 6 && ns_threshold_output(custody[i], k, &output) == NS_OK);
            assert(output.len < NS_MAX_MESSAGE);
            memcpy(custody_packets[written], output.data, output.len);
            custody_packets[written++][output.len] = 0;
            if (!i) {
                uint8_t expected[NS_MAX_FRAME];
                size_t length;
                assert(ns_encode_frame(output.data, output.len, 0, expected, sizeof(expected),
                                       &length) == NS_OK);
                assert(test_qr_len == length && !memcmp(test_qr, expected, length));
                tap(60, 442);
            }
        }
        if (i)
            ns_finish_response(custody[i]);
    }
    return written;
}
static void custody_route(unsigned count) {
    for (unsigned i = 0; i < count; i++) {
        char recipient[65];
        public_field(custody_packets[i], "recipient", recipient);
        unsigned device = 0;
        while (device < 3 && strcmp(recipient, custody_keys[device]))
            device++;
        assert(device < 3);
        custody_feed(device, (uint8_t *)custody_packets[i], strlen(custody_packets[i]));
    }
}
static void threshold_flow_test(void) {
    testing = true;
    custody[0] = device_core();
    assert(!ns_is_loaded(custody[0]));
    tap(140, 175);
    tap(140, 349);
    assert(!strcmp(visible_title, "2-of-3 group"));
    save_frame("20-group-intro");
    tap(215, 442);
    assert(ns_threshold_state(custody[0]) == NS_THRESHOLD_JOIN);
    save_frame("21-group-join");
    for (unsigned i = 0; i < 3; i++) {
        if (i) {
            custody[i] = (ns_context *)peer_storage[i - 1];
            assert(ns_init(peer_storage[i - 1], NS_CONTEXT_BYTES) == NS_OK);
            uint8_t random[32];
            assert(platform_random32(random));
            assert(ns_threshold_start(custody[i], random, clock_ms) == NS_OK);
        }
        ns_text output;
        assert(ns_threshold_output(custody[i], 0, &output) == NS_OK);
        char join[256];
        assert(output.len < sizeof(join));
        memcpy(join, output.data, output.len);
        join[output.len] = 0;
        public_field(join, "key", custody_keys[i]);
    }
    assert(custody_collect() == 3 && scanning);
    char sorted[3][65];
    memcpy(sorted, custody_keys, sizeof(sorted));
    qsort(sorted, 3, sizeof(sorted[0]), public_key_order);
    char setup[512];
    int n = snprintf(
        setup, sizeof(setup),
        "{\"type\":\"nsealr_setup\",\"session\":\"%064u\",\"members\":[\"%s\",\"%s\",\"%s\"]}", 1u,
        sorted[0], sorted[1], sorted[2]);
    assert(n > 0 && (size_t)n < sizeof(setup));
    for (unsigned i = 0; i < 3; i++) {
        custody_feed(i, (uint8_t *)setup, (size_t)n);
        if (i)
            peer_approve(i);
    }
    save_frame("22-group-review");
    finish_visible_review();
    save_frame("23-group-exchange");
    assert(custody_collect() == 6 && scanning);
    custody_route(6);
    assert(custody_collect() == 6 && scanning);
    custody_route(6);
    assert(ns_is_loaded(custody[0]) && ns_threshold_state(custody[0]) == NS_THRESHOLD_READY);
    assert(custody_collect() == 3);
    assert(!strcmp(visible_title, "Group ready"));
    save_frame("24-group-ready");
    uint8_t group_key[64];
    size_t written;
    assert(ns_public_key(custody[0], 0, group_key, sizeof(group_key), &written) == NS_OK);
    for (unsigned i = 0; i < 2; i++)
        assert(ns_threshold_backup(custody[i], custody_backups[i], sizeof(custody_backups[i]),
                                   &custody_backup_len[i]) == NS_OK);
    tap(140, 175);
    assert(!strcmp(visible_title, "Back up share"));
    tap(215, 442);
    save_frame("25-share-backup");
    tap(215, 442);
    char paused[100];
    snprintf(paused, sizeof(paused), "%s", visible_caption);
    clock_ms += 1000;
    device_tick(clock_ms);
    assert(!strcmp(paused, visible_caption));
    tap(258, 122);
    assert(strcmp(paused, visible_caption));
    tap(60, 442);
    tap(140, 175);
    custody_feed(0, custody_backups[1], custody_backup_len[1]);
    assert(!strcmp(visible_title, "Different backup") && ns_is_loaded(custody[0]));
    tap(215, 442);
    custody_feed(0, custody_backups[0], custody_backup_len[0]);
    assert(!strcmp(visible_title, "Backup checked"));
    tap(215, 442);
    tap(140, 233);
    tap(258, 122);
    assert(!strcmp(visible_title, "Group record"));
    save_frame("26-group-record");
    tap(270, 26);
    tap(140, 233);
    tap(140, 349);
    custody_feed(0, custody_backups[0], custody_backup_len[0]);
    assert(!ns_is_loaded(custody[0]));
    save_frame("27-share-recovery");
    finish_visible_review();
    tap(60, 442);
    assert(!strcmp(visible_title, "Share restored") && ns_is_loaded(custody[0]));
    tap(140, 291);
    char members[2][65];
    memcpy(members[0], custody_keys[0], 65);
    memcpy(members[1], custody_keys[1], 65);
    qsort(members, 2, sizeof(members[0]), public_key_order);
    char request[1024];
    n = snprintf(request, sizeof(request),
                 "{\"type\":\"nsealr_sign\",\"id\":\"native-group\",\"session\":\"%064u\","
                 "\"members\":[\"%s\",\"%s\"],\"event\":\"{\\\"pubkey\\\":\\\"%.*s\\\","
                 "\\\"created_at\\\":1794211200,\\\"kind\\\":1,\\\"tags\\\":[],"
                 "\\\"content\\\":\\\"Two shares, one Nostr identity.\\\"}\"}",
                 2u, members[0], members[1], 64, group_key);
    assert(n > 0 && (size_t)n < sizeof(request));
    tap(140, 175);
    custody_feed(0, (uint8_t *)request, (size_t)n);
    custody_feed(1, (uint8_t *)request, (size_t)n);
    peer_approve(1);
    finish_visible_review();
    assert(custody_collect() == 2);
    custody_route(2);
    assert(custody_collect() == 2);
    custody_route(2);
    assert(ns_threshold_state(custody[0]) == NS_THRESHOLD_RESULT);
    save_frame("28-group-signed");
    assert(custody_collect() == 2);
    assert(!strcmp(custody_packets[0], custody_packets[1]));
    assert(strstr(custody_packets[0], "Two shares, one Nostr identity."));
    assert(ns_is_loaded(custody[0]));
    tap(270, 26);
    for (unsigned i = 1; i < 3; i++)
        ns_deinit(custody[i]);
    platform_wipe(custody_backups, sizeof(custody_backups));
    testing = false;
    puts("PASS: real 3-device setup, all packets, animated share backup/check/recovery, "
         "rendered group consent and 2-device signing through actual UI input");
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
    if (argc == 2 && !strcmp(argv[1], "--test")) {
        flow_test();
        threshold_flow_test();
    } else if (argc == 3 && !strcmp(argv[1], "--render")) {
        render_dir = argv[2];
        flow_test();
        threshold_flow_test();
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
