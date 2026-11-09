#include "device.h"
#include "secret_qr.h"
#include "secret_raster.h"
#include "src/libs/qrcode/qrcodegen.h"
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

/* A host simulator uses published test entropy. The P4 supplies qualified RNG.
 */
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
static char visible_title[80], visible_caption[100], visible_right[40], visible_left[40],
    visible_aux[40], visible_header[40];
/* Test inspection is enabled only for the published, deterministic test
 * vectors. */
static bool testing;
static char test_lines[8][14];
static uint8_t test_qr[NS_MAX_FRAME];
static size_t test_qr_len;
static bool test_media_available;
static const char *test_share_path = ".cache/ui-preview/NSEALR.NSR";

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
/* Host-only fixtures. These are not camera, battery or entropy measurements. */
static unsigned simulated_power = DEVICE_POWER_BATTERY, simulated_brightness = 100;
static bool simulated_photo, simulated_capture;
static unsigned simulated_photo_start;
unsigned platform_power_state(void) { return simulated_power; }
bool platform_display_brightness(unsigned percent) {
    simulated_brightness = percent;
    return percent >= 20 && percent <= 100;
}
bool platform_photo_start(void) {
    simulated_photo = true;
    simulated_capture = false;
    simulated_photo_start++;
    for (unsigned y = 166; y < 358; y++)
        for (unsigned x = 32; x < 288; x++) {
            size_t at = ((size_t)y * 320 + x) * 3;
            pixels[at] = (uint8_t)x;
            pixels[at + 1] = (uint8_t)y;
            pixels[at + 2] = 128;
        }
    return true;
}
bool platform_photo_capture(void) {
    simulated_capture = simulated_photo;
    return simulated_capture;
}
bool platform_photo_stop(void) {
    simulated_photo = simulated_capture = false;
    return true;
}
bool platform_photo_take(uint8_t digest[32]) {
    if (!simulated_photo || !simulated_capture)
        return false;
    memset(digest, 0x5a, 32);
    return platform_photo_stop();
}
bool platform_secret_qr_size(const uint8_t *p, size_t n, unsigned *modules) {
    bool ok = p4_secret_qr_encode(&secret_qr, p, n);
    if (ok)
        *modules = secret_qr.modules;
    p4_secret_qr_clear(&secret_qr);
    return ok;
}
bool platform_secret_qr_region(const uint8_t *p, size_t n, unsigned col, unsigned row) {
    if (!p4_secret_qr_encode(&secret_qr, p, n))
        return false;
    if (col * 5 >= secret_qr.modules || row * 5 >= secret_qr.modules)
        return false;
    for (unsigned y = 0; y < 250; y++)
        for (unsigned x = 0; x < 250; x++) {
            unsigned mx = col * 5 + x / 50, my = row * 5 + y / 50;
            uint8_t value = mx >= secret_qr.modules || my >= secret_qr.modules        ? 100
                            : qrcodegen_getModule(secret_qr.matrix, (int)mx, (int)my) ? 0
                                                                                      : 255;
            if (!(x % 50) || !(y % 50))
                value = 170;
            size_t at = ((size_t)(148 + y) * 320 + 35 + x) * 3;
            memset(pixels + at, value, 3);
        }
    p4_secret_qr_clear(&secret_qr);
    secrets_visible = true;
    return true;
}

/* Native file tests exercise the local contract; physical SD uses FatFs. */
share_file_result platform_share_save(const uint8_t *bytes, size_t length) {
    if (!test_media_available)
        return SHARE_FILE_UNAVAILABLE;
    if (!length || length > NS_THRESHOLD_MAX_BACKUP)
        return SHARE_FILE_INVALID;
    int fd = open(test_share_path, O_RDWR | O_CREAT | O_EXCL, 0600);
    if (fd < 0)
        return errno == EEXIST ? SHARE_FILE_EXISTS : SHARE_FILE_IO;
    uint8_t check[NS_THRESHOLD_MAX_BACKUP];
    bool ok = write(fd, bytes, length) == (ssize_t)length && fsync(fd) == 0 &&
              lseek(fd, 0, SEEK_SET) == 0 && read(fd, check, length) == (ssize_t)length &&
              !memcmp(bytes, check, length);
    if (close(fd))
        ok = false;
    platform_wipe(check, sizeof(check));
    if (!ok)
        (void)unlink(test_share_path);
    return ok ? SHARE_FILE_OK : SHARE_FILE_IO;
}
share_file_result platform_share_load(uint8_t *bytes, size_t capacity, size_t *written) {
    *written = 0;
    platform_wipe(bytes, capacity);
    if (!test_media_available)
        return SHARE_FILE_UNAVAILABLE;
    int fd = open(test_share_path, O_RDONLY | O_NOFOLLOW);
    if (fd < 0)
        return errno == ENOENT ? SHARE_FILE_MISSING : SHARE_FILE_IO;
    struct stat st;
    share_file_result result = SHARE_FILE_IO;
    if (fstat(fd, &st) || !S_ISREG(st.st_mode))
        goto done;
    if (st.st_size <= 0 || st.st_size > (off_t)capacity || st.st_size > NS_THRESHOLD_MAX_BACKUP) {
        result = SHARE_FILE_INVALID;
        goto done;
    }
    if (read(fd, bytes, (size_t)st.st_size) == st.st_size) {
        *written = (size_t)st.st_size;
        result = SHARE_FILE_OK;
    }
done:
    if (close(fd))
        result = SHARE_FILE_IO;
    if (result != SHARE_FILE_OK) {
        platform_wipe(bytes, capacity);
        *written = 0;
    }
    return result;
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
    snprintf(visible_left, sizeof(visible_left), "%s", view->left_label ? view->left_label : "");
    snprintf(visible_aux, sizeof(visible_aux), "%s", view->aux_label ? view->aux_label : "");
    snprintf(visible_header, sizeof(visible_header), "%s",
             view->header_label ? view->header_label : "");
    ui_show(view, callback, NULL);
    presenting = true;
    draw();
    presenting = false;
    if (view->screen == UI_PHOTO && simulated_capture) {
        for (unsigned y = 166; y < 358; y++)
            for (unsigned x = 32; x < 288; x++) {
                size_t at = ((size_t)y * 320 + x) * 3;
                pixels[at] = (uint8_t)x;
                pixels[at + 1] = (uint8_t)y;
                pixels[at + 2] = 128;
            }
    }
    lv_obj_t *reader = ui_reader();
    device_presented(reader && lv_obj_get_scroll_bottom(reader) <= 1);
    return true;
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
static void clear_loaded(void) {
    tap(270, 26);
    assert(!strcmp(visible_title, "Clear this key?"));
    tap(215, 442);
    assert(!ns_is_loaded(device_core()));
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
    printf("PASS: %u-word recovery entry: %u pointer taps; %u extra "
           "Back/navigation checks\n",
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
    tap(37 + (int)(i % 6) * 49, 227 + (int)(i / 6) * 38);
}
static void feed_message(const char *input) {
    size_t length = strlen(input);
    for (unsigned i = 0; i < (length + NS_QR_CHUNK - 1) / NS_QR_CHUNK; i++) {
        uint8_t frame[NS_MAX_FRAME];
        size_t size = 0;
        assert(ns_encode_frame((const uint8_t *)input, length, i, frame, sizeof(frame), &size) ==
               NS_OK);
        device_scan_bytes(frame, size);
        for (size_t j = 0; j < size; j++)
            assert(frame[j] == 0);
    }
}
static void feed_request(const char *event) {
    char input[NS_MAX_MESSAGE];
    int n =
        snprintf(input, sizeof(input),
                 "{\"id\":\"native-flow\",\"method\":\"sign_event\",\"params\":[\"%s\"]}", event);
    assert(n > 0 && (size_t)n < sizeof(input));
    feed_message(input);
}
static void refused_request_test(void) {
    feed_message("{\"id\":\"native-refused\",\"method\":\"unsupported\",\"params\":[]}");
    ns_text response;
    assert(!scanning && !strcmp(visible_title, "Request refused"));
    assert(ns_review_count(device_core()) == 0);
    assert(ns_response(device_core(), &response) == NS_OK);
    const char expected[] = "{\"id\":\"native-refused\",\"error\":\"Unsupported "
                            "operation or event semantics\"}";
    assert(response.len == sizeof(expected) - 1 && !memcmp(response.data, expected, response.len));
    uint8_t frame[NS_MAX_FRAME];
    size_t length;
    assert(ns_encode_frame(response.data, response.len, 0, frame, sizeof(frame), &length) == NS_OK);
    assert(test_qr_len == length && !memcmp(test_qr, frame, length));
    assert(!strcmp(visible_left, "Done") && !strcmp(visible_right, "Reason") && !visible_aux[0]);
    save_frame("35-request-refused");
    tap(215, 442);
    assert(ui_reader() && !strcmp(visible_title, "Request refused"));
    save_frame("36-refusal-reason");
    tap(60, 442);
    assert(!ui_reader() && test_qr_len == length && !memcmp(test_qr, frame, length));
    tap(60, 442);
    assert(ns_response(device_core(), &response) != NS_OK && ns_is_loaded(device_core()));
    /* JSON escaping can make a bounded request ID span multiple response frames.
     */
    char multi[1024] = "{\"id\":\"";
    for (unsigned i = 0; i < 128; i++)
        strcat(multi, "\\u0001");
    strcat(multi, "\",\"method\":\"unsupported\",\"params\":[]}");
    tap(140, 175);
    feed_message(multi);
    assert(!strcmp(visible_left, "Done") && !strcmp(visible_right, "Pause") &&
           !strcmp(visible_aux, "Next") && !strcmp(visible_header, "Reason"));
    assert(ns_response(device_core(), &response) == NS_OK && response.len > NS_QR_CHUNK);
    tap(258, 122);
    assert(ns_encode_frame(response.data, response.len, 1, frame, sizeof(frame), &length) == NS_OK);
    assert(test_qr_len == length && !memcmp(test_qr, frame, length));
    save_frame("42-refusal-multiple-frames");
    tap(170, 26);
    assert(ui_reader());
    tap(60, 442);
    assert(!strcmp(visible_right, "Resume") && test_qr_len == length &&
           !memcmp(test_qr, frame, length));
    tap(60, 442);
    assert(ns_response(device_core(), &response) != NS_OK);
    tap(140, 175);
    uint8_t invalid[] = "invalid";
    device_scan_bytes(invalid, sizeof(invalid) - 1);
    assert(!strcmp(visible_title, "Please check") &&
           ns_response(device_core(), &response) != NS_OK);
    tap(215, 442);
    tap(140, 175);
    puts("PASS: validated-id refusal QR/reason/Done, unchanged returned bytes, "
         "malformed "
         "input without a reply and subsequent normal request");
}
static void flow_test(void) {
    testing = true;
    save_frame("01-home");
    tap(140, 233);
    save_frame("02-load");
    tap(140, 175);
    uint8_t compact[16] = {0};
    device_scan_bytes(compact, sizeof(compact));
    assert(ns_is_loaded(device_core()) && ns_word_count(device_core()) == 12);
    save_frame("03-identity");
    uint8_t original[64], restored[64];
    size_t n = 0;
    assert(ns_public_key(device_core(), 0, original, sizeof(original), &n) == NS_OK && n == 64);
    tap(140, 175);
    tap(140, 291);
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
    clear_loaded();
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
    refused_request_test();
    char event[1024];
    int wrote = snprintf(event, sizeof(event),
                         "{\\\"pubkey\\\":\\\"%.*s\\\",\\\"created_at\\\":"
                         "1794211200,\\\"kind\\\":1,"
                         "\\\"tags\\\":[],\\\"content\\\":\\\"Hello from an "
                         "offline Nostr signer.\\\"}",
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
    clear_loaded();
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
                     "{\\\"pubkey\\\":\\\"%.*s\\\",\\\"created_at\\\":1794211200,"
                     "\\\"kind\\\":1,"
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
    clear_loaded();
    assert(!ns_is_loaded(device_core()));

    tap(140, 233);
    tap(140, 233);
    tap(140, 233);
    enter_public_words(24, false);
    complete_word_review(24);
    assert(ns_is_loaded(device_core()) && ns_word_count(device_core()) == 24);
    uint8_t plain24[64], with_pass[64];
    assert(ns_public_key(device_core(), 0, plain24, sizeof(plain24), &n) == NS_OK);
    tap(140, 233);
    tap(215, 442);
    tap(60, 442);
    assert(!strcmp(visible_title, "Public identity"));
    tap(60, 442);
    assert(!strcmp(visible_title, "Identity ready"));
    tap(140, 175);
    tap(140, 349);
    assert(!strcmp(visible_title, "Identity ready"));
    tap(140, 291);
    save_frame("31-passphrase-purpose");
    tap(140, 175);
    text_key('t');
    text_key('e');
    text_key('s');
    text_key('t');
    tap(135, 186);
    assert(!strcmp(test_lines[0], "test[ ]|"));
    tap(233, 186);
    assert(!strcmp(test_lines[0], "test|[ ]"));
    tap(184, 186);
    text_key('t');
    assert(!strcmp(test_lines[0], "test|[ ]"));
    save_frame("52-passphrase-editor");
    tap(282, 186);
    tap(215, 442);
    assert(!strcmp(visible_title, "Check passphrase"));
    save_frame("16-passphrase-review");
    tap(215, 442);
    assert(ns_public_key(device_core(), 0, with_pass, sizeof(with_pass), &n) == NS_OK &&
           memcmp(plain24, with_pass, 64));
    tap(140, 349);
    tap(86, 227);
    tap(215, 442);
    assert(!strcmp(visible_title, "Passphrase"));
    tap(60, 442);
    assert(!strcmp(visible_title, "Identity ready") && strstr(visible_caption, "account 0"));
    assert(ns_public_key(device_core(), 0, restored, sizeof(restored), &n) == NS_OK &&
           !memcmp(with_pass, restored, 64));
    tap(140, 291);
    tap(140, 175);
    for (unsigned i = 0; i < 80; i++)
        tap(135, 186);
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
    tap(140, 291);
    tap(140, 233);
    assert(scanning && !strcmp(visible_title, "Scan passphrase"));
    save_frame("33-passphrase-scan");
    tap(60, 442);
    assert(!scanning && !strcmp(visible_title, "Identity ready"));
    assert(ns_public_key(device_core(), 0, restored, sizeof(restored), &n) == NS_OK &&
           !memcmp(with_pass, restored, 64));
    tap(140, 291);
    tap(140, 233);
    uint8_t invalid_pass[] = {0xc0, 0x80};
    device_scan_bytes(invalid_pass, sizeof(invalid_pass));
    assert(!strcmp(visible_title, "Please check") && ns_is_loaded(device_core()));
    assert(!invalid_pass[0] && !invalid_pass[1]);
    tap(215, 442);
    tap(140, 291);
    tap(140, 233);
    uint8_t oversized_pass[257];
    memset(oversized_pass, 'a', sizeof(oversized_pass));
    device_scan_bytes(oversized_pass, sizeof(oversized_pass));
    assert(!strcmp(visible_title, "Please check") && ns_is_loaded(device_core()));
    for (size_t i = 0; i < sizeof(oversized_pass); i++)
        assert(!oversized_pass[i]);
    tap(215, 442);
    tap(140, 291);
    tap(140, 233);
    uint8_t composed_pass[] = {0xc3, 0xa9, 0xe2, 0x82, 0xac};
    device_scan_bytes(composed_pass, sizeof(composed_pass));
    assert(!scanning && !strcmp(visible_title, "Check passphrase"));
    for (size_t i = 0; i < sizeof(composed_pass); i++)
        assert(!composed_pass[i]);
    assert(ns_public_key(device_core(), 0, restored, sizeof(restored), &n) == NS_OK &&
           !memcmp(with_pass, restored, 64));
    save_frame("34-unicode-passphrase");
    tap(60, 442);
    tap(184, 186);
    tap(215, 442);
    assert(!strcmp(visible_title, "Check passphrase"));
    tap(215, 442);
    assert(ns_public_key(device_core(), 0, with_pass, sizeof(with_pass), &n) == NS_OK);
    tap(140, 291);
    tap(140, 233);
    uint8_t decomposed_pass[] = {'e', 0xcc, 0x81};
    device_scan_bytes(decomposed_pass, sizeof(decomposed_pass));
    tap(215, 442);
    assert(ns_public_key(device_core(), 0, restored, sizeof(restored), &n) == NS_OK &&
           !memcmp(with_pass, restored, 64));
    _Alignas(NS_CONTEXT_ALIGN) uint8_t expected_storage[NS_CONTEXT_BYTES];
    ns_context *expected_identity = (ns_context *)expected_storage;
    uint8_t public_words[256], public_pass[] = {'e', 0xcc, 0x81}, expected_key[64];
    size_t words_len;
    assert(ns_backup(device_core(), 2, public_words, sizeof(public_words), &words_len) == NS_OK);
    assert(ns_init(expected_storage, sizeof(expected_storage)) == NS_OK);
    assert(ns_import_mnemonic(expected_identity, public_words, words_len, public_pass,
                              sizeof(public_pass), 1) == NS_OK);
    assert(ns_public_key(expected_identity, 0, expected_key, sizeof(expected_key), &n) == NS_OK);
    ns_deinit(expected_identity);
    tap(140, 349);
    tap(86, 227);
    tap(215, 442);
    tap(140, 233);
    uint8_t account_pass[] = {0xc3, 0xa9};
    device_scan_bytes(account_pass, sizeof(account_pass));
    assert(ns_public_key(device_core(), 0, restored, sizeof(restored), &n) == NS_OK &&
           !memcmp(with_pass, restored, 64));
    tap(215, 442);
    assert(strstr(visible_caption, "account 1"));
    assert(ns_public_key(device_core(), 0, with_pass, sizeof(with_pass), &n) == NS_OK &&
           !memcmp(with_pass, expected_key, 64));
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
    clear_loaded();
    assert(!ns_is_loaded(device_core()));
    testing = false;

    char escaped[80];
    size_t escaped_len = 0;
    const uint8_t tricky[] = {0x61, 0xe2, 0x80, 0xae, 0x5c, 0x62, 0x00};
    assert(ui_escape_text(tricky, sizeof(tricky), escaped, sizeof(escaped), &escaped_len));
    assert(!strcmp(escaped, "a\\u{202e}\\\\b\\u{0}"));
    const uint8_t invalid[] = {0xc0, 0x80};
    assert(!ui_escape_text(invalid, sizeof(invalid), escaped, sizeof(escaped), &escaped_len));
    puts("PASS: real-core load/backup/clear/restore; QR frame collection; "
         "rendered review; sign, "
         "reject, cancel, response and session clear");
    puts("PASS: confirmation return/options, cancelled account preservation, "
         "local UTF8 "
         "passphrase scan/review/edit, invalid/oversize rejection and "
         "NFKD-equivalent identity");
}
/* These fixtures check controller transitions, not physical camera or power. */
static void load_zero_words(unsigned count) {
    static const char *last[] = {"about", "address", "agent", "admit", "art"};
    uint8_t words[256] = {0};
    for (unsigned i = 1; i < count; i++)
        strcat((char *)words, "abandon ");
    strcat((char *)words, last[(count - 12) / 3]);
    tap(140, 175);
    assert(scanning);
    device_scan_bytes(words, strlen((char *)words));
    assert(ns_is_loaded(device_core()) && ns_word_count(device_core()) == count);
}
static void quiz_words(unsigned count) {
    static const char *last[] = {"about", "address", "agent", "admit", "art"};
    for (unsigned i = 0; i < count; i++) {
        unsigned position = 0;
        assert(sscanf(visible_title, "Choose word %u", &position) == 1);
        const char *expected = position == count ? last[(count - 12) / 3] : "abandon";
        unsigned choice = 0;
        while (choice < 4 && strcmp(test_lines[choice], expected))
            choice++;
        assert(choice < 4);
        tap(140, 162 + (int)choice * 56);
    }
    assert(!strcmp(visible_title, "Backup checked"));
    tap(215, 442);
}
static void signer_flow_test(void) {
    testing = true;
    /* Brightness uses the platform, and session preferences do not retain keys.
     */
    tap(140, 291);
    tap(140, 349);
    tap(140, 175);
    assert(simulated_brightness == 60);
    tap(140, 175);
    tap(140, 175);
    assert(simulated_brightness == 100);
    tap(140, 233);
    tap(140, 233);
    tap(140, 233);
    save_frame("43-display-settings");
    tap(60, 442);
    tap(60, 442);
    /* Photo fixture is visibly synthetic, with accept, retake and cancel paths.
     */
    tap(140, 291);
    tap(140, 175);
    tap(140, 175);
    assert(simulated_photo && !simulated_capture);
    save_frame("44-camera-fixture");
    tap(215, 442);
    assert(simulated_capture && !strcmp(visible_title, "Use this picture?"));
    save_frame("53-camera-frozen-fixture");
    unsigned starts = simulated_photo_start;
    tap(60, 442);
    assert(simulated_photo_start == starts + 1 && !simulated_capture);
    tap(215, 442);
    tap(215, 442);
    assert(!simulated_photo && !strcmp(visible_title, "Recovery words"));
    tap(140, 175);
    assert(ns_is_loaded(device_core()) && ns_word_count(device_core()) == 12);
    tap(140, 175);
    assert(!strcmp(visible_title, "Secret backup"));
    clear_loaded();
    tap(140, 291);
    tap(140, 175);
    tap(140, 175);
    tap(60, 442);
    assert(!simulated_photo && !ns_is_loaded(device_core()));
    tap(140, 291);
    tap(140, 175);
    tap(140, 175);
    clock_ms += 600001;
    device_tick(clock_ms);
    assert(!simulated_photo && !ns_is_loaded(device_core()));
    /* Published independent dice vectors, entered through real pointer buttons.
     */
    for (unsigned variant = 0; variant < 2; variant++) {
        tap(140, 291);
        tap(140, 175);
        tap(140, 233);
        tap(140, variant ? 233 : 175);
        tap(215, 442);
        assert(!strcmp(visible_title, "Roll dice"));
        tap(60, 247);
        tap(60, 371);
        assert(strstr(visible_caption, "0 of"));
        tap(60, 247);
        tap(215, 371);
        assert(strstr(visible_caption, "0 of"));
        unsigned count = variant ? 100 : 50;
        for (unsigned i = 0; i < count; i++) {
            unsigned die = variant ? 5 - i % 6 : i % 6;
            tap(62 + (int)(die % 3) * 98, 247 + (int)(die / 3) * 60);
        }
        save_frame(variant ? "46-dice-100" : "45-dice-50");
        tap(215, 442);
        assert(!strcmp(visible_title, "Use these rolls?"));
        tap(60, 442);
        assert(!strcmp(visible_title, "Roll dice"));
        tap(215, 442);
        tap(215, 442);
        assert(ns_word_count(device_core()) == (variant ? 24 : 12));
        uint8_t key[64];
        size_t length;
        assert(ns_public_key(device_core(), 0, key, sizeof(key), &length) == NS_OK && length == 64);
        const char *expected =
            variant ? "46af5629c6dab5ec4c666c94636a1ef5b103008713f0339d517c342df9275cd5"
                    : "99b6e95ef71c899a4bd8561a3c2fc1920a5b2da85e50c72a9a054a14168a543"
                      "5";
        assert(!memcmp(key, expected, 64));
        clear_loaded();
    }
    for (unsigned count = 12; count <= 24; count += 3) {
        load_zero_words(count);
        tap(140, 175);
        tap(140, 291);
        if (count != 12 && count != 24) {
            /* Unsupported SeedQR exports must not be offered. */
            tap(140, 291);
            assert(!strcmp(visible_title, "Back up identity"));
        }
        tap(140, 175);
        for (unsigned i = 0; i < (count + 5) / 6; i++)
            tap(215, 442);
        tap(140, 175);
        quiz_words(count);
        if (count == 12) {
            tap(140, 291);
            tap(140, 233);
            uint8_t qr[96];
            size_t length;
            assert(ns_backup(device_core(), 3, qr, sizeof(qr), &length) == NS_OK);
            tap(258, 122);
            assert(!strcmp(visible_title, "Copy SeedQR"));
            unsigned block, total;
            assert(sscanf(visible_caption, "Block %u/%u", &block, &total) == 2 && block == 1);
            save_frame("47-copy-seedqr");
            tap(215, 442);
            tap(60, 442);
            for (unsigned i = 1; i < total; i++)
                tap(215, 442);
            save_frame("48-copy-seedqr-last");
            assert(!strcmp(visible_right, "Scan to check"));
            tap(215, 442);
            assert(scanning);
            device_scan_bytes(qr, length);
            assert(!strcmp(visible_title, "Backup checked"));
            tap(215, 442);
        }
        clear_loaded();
    }
    /* Scan first, then load and deliberately resume the saved request. */
    tap(140, 175);
    feed_message("{\"id\":\"scan-first\",\"method\":\"get_public_key\",\"params\":[]}");
    assert(ns_has_staged_request(device_core()) && !ns_is_loaded(device_core()));
    assert(!strcmp(visible_title, "Load a key"));
    save_frame("49-scan-first-load");
    tap(140, 175);
    uint8_t zero[16] = {0};
    device_scan_bytes(zero, sizeof(zero));
    assert(ns_has_staged_request(device_core()) && ns_is_loaded(device_core()));
    tap(140, 175);
    assert(!ns_has_staged_request(device_core()) && ui_reader());
    while (lv_obj_get_scroll_bottom(ui_reader()) > 1)
        drag(260, 370, 180);
    tap(215, 442);
    tap(140, 175);
    ns_text response;
    assert(ns_response(device_core(), &response) == NS_OK);
    tap(60, 442);
    clear_loaded();
    tap(140, 175);
    feed_request(
        "{\\\"pubkey\\\":\\\"99b6e95ef71c899a4bd8561a3c2fc1920a5b2da85e50c72a9a054a14168a5435\\\","
        "\\\"created_at\\\":1794211200,\\\"kind\\\":1,\\\"tags\\\":[],\\\"content\\\":\\\"Wrong "
        "key\\\"}");
    assert(ns_has_staged_request(device_core()));
    tap(140, 175);
    device_scan_bytes(zero, sizeof(zero));
    tap(140, 175);
    assert(!strcmp(visible_title, "Request refused") &&
           ns_response(device_core(), &response) == NS_OK);
    assert(!ns_has_staged_request(device_core()) && !ns_review_count(device_core()));
    tap(60, 442);
    clear_loaded();
    tap(140, 175);
    feed_message("{\"id\":\"cancel-stage\",\"method\":\"get_public_key\",\"params\":[]}");
    tap(60, 442);
    assert(!ns_has_staged_request(device_core()) && !ns_is_loaded(device_core()));
    /* User activity extends only the idle window, never a staged deadline. */
    tap(140, 175);
    feed_message("{\"id\":\"expires\",\"method\":\"get_public_key\",\"params\":[]}");
    tap(140, 175);
    device_scan_bytes(zero, sizeof(zero));
    clock_ms += 590000;
    tap(140, 233);
    clock_ms += 20000;
    device_tick(clock_ms);
    assert(!ns_has_staged_request(device_core()) && ns_is_loaded(device_core()));
    tap(140, 233);
    clock_ms += 590000;
    device_action(UI_READER_END);
    clock_ms += 20000;
    device_tick(clock_ms);
    assert(!ns_is_loaded(device_core()));
    /* Session clear is explicit and can be cancelled without dropping the key. */
    load_zero_words(12);
    tap(270, 26);
    assert(ns_is_loaded(device_core()) && !strcmp(visible_title, "Clear this key?"));
    save_frame("50-clear-key");
    tap(60, 442);
    assert(ns_is_loaded(device_core()));
    /* A powered cable or unknown state blocks input and immediately clears keys.
     */
    simulated_power = DEVICE_POWER_EXTERNAL;
    device_tick(clock_ms);
    assert(!ns_is_loaded(device_core()) && !strcmp(visible_title, "Use battery power"));
    tap(140, 175);
    assert(!scanning);
    save_frame("51-external-power-fixture");
    simulated_power = DEVICE_POWER_UNKNOWN;
    device_tick(clock_ms);
    assert(!strcmp(visible_title, "Check battery power"));
    simulated_power = DEVICE_POWER_BATTERY;
    device_tick(clock_ms);
    assert(!strcmp(visible_title, "Your Nostr key"));
    testing = false;
    puts("PASS: camera fixture capture/retake/accept/cancel/idle cleanup; "
         "independent 50/100-roll dice UI vectors");
    puts("PASS: all five word-count quizzes, supported QR menus, paper block "
         "navigation and scan-back");
    puts("PASS: scan-first load/resume, fixed request expiry, idle clear, "
         "deliberate clear and simulated power gating");
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
    tap(140, 291);
    tap(140, 233);
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
    int n = snprintf(setup, sizeof(setup),
                     "{\"type\":\"nsealr_setup\",\"session\":\"%064u\","
                     "\"members\":[\"%s\",\"%s\",\"%s\"]}",
                     1u, sorted[0], sorted[1], sorted[2]);
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
    tap(140, 233);
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
    assert(!ns_threshold_output_count(custody[0]));
    uint8_t record[1024], encoded[NS_MAX_FRAME];
    size_t record_len, encoded_len;
    assert(ns_threshold_record(custody[0], record, sizeof(record), &record_len) == NS_OK);
    tap(215, 442);
    assert(ns_encode_frame(record, record_len, 0, encoded, sizeof(encoded), &encoded_len) == NS_OK);
    assert(test_qr_len == encoded_len && !memcmp(test_qr, encoded, encoded_len));
    assert(!ns_threshold_output_count(custody[0]));
    save_frame("32-group-record-qr");
    tap(258, 122);
    assert(ns_encode_frame(record, record_len, 1, encoded, sizeof(encoded), &encoded_len) == NS_OK);
    assert(test_qr_len == encoded_len && !memcmp(test_qr, encoded, encoded_len));
    tap(60, 442);
    assert(!strcmp(visible_title, "Group record"));
    tap(60, 442);
    assert(!strcmp(visible_title, "Public identity"));
    clear_loaded();
    tap(140, 291);
    tap(140, 291);
    tap(140, 175);
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
    tap(60, 442);
    assert(ns_is_loaded(custody[0]) && ns_threshold_state(custody[0]) == NS_THRESHOLD_READY &&
           !ns_threshold_output_count(custody[0]));
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
    /* Local media remains an explicit action; missing card and existing file
     * preserve the current share, and restore still needs group consent. */
    (void)unlink(test_share_path);
    test_media_available = false;
    tap(140, 291);
    tap(140, 175);
    save_frame("29-share-file-consent");
    tap(215, 442);
    assert(!strcmp(visible_title, "Please check") && ns_is_loaded(custody[0]));
    tap(215, 442);
    test_media_available = true;
    tap(140, 175);
    tap(215, 442);
    assert(!strcmp(visible_title, "Share saved"));
    save_frame("30-share-file-saved");
    tap(215, 442);
    tap(140, 291);
    tap(140, 175);
    tap(215, 442);
    assert(!strcmp(visible_title, "Please check") && ns_is_loaded(custody[0]));
    uint8_t saved[NS_THRESHOLD_MAX_BACKUP];
    size_t saved_len;
    assert(platform_share_load(saved, sizeof(saved), &saved_len) == SHARE_FILE_OK);
    assert(saved_len == custody_backup_len[0] && !memcmp(saved, custody_backups[0], saved_len));
    platform_wipe(saved, sizeof(saved));
    clear_loaded();
    tap(140, 291);
    tap(140, 291);
    tap(140, 233);
    assert(!ns_is_loaded(custody[0]) && ui_reader());
    finish_visible_review();
    tap(60, 442);
    assert(ns_is_loaded(custody[0]));
    uint8_t restored[64];
    assert(ns_public_key(custody[0], 0, restored, sizeof(restored), &written) == NS_OK &&
           !memcmp(group_key, restored, 64));
    uint8_t old_record[1024], fingerprint[64];
    size_t old_record_len;
    uint32_t lost_member;
    assert(ns_threshold_record(custody[1], old_record, sizeof(old_record) - 1, &old_record_len) ==
           NS_OK);
    old_record[old_record_len] = 0;
    assert(ns_threshold_info(custody[0], fingerprint, &lost_member) == NS_OK);
    const char *descriptor_start = strstr((const char *)old_record, "\"descriptor\":\"");
    assert(descriptor_start);
    descriptor_start += strlen("\"descriptor\":\"");
    char descriptor[461];
    memcpy(descriptor, descriptor_start, 460);
    descriptor[460] = 0;
    assert(descriptor_start[460] == '"');
    clear_loaded();
    tap(140, 291);
    tap(140, 291);
    tap(140, 291);
    assert(!strcmp(visible_title, "Repair lost share"));
    save_frame("37-repair-entry");
    tap(60, 442);
    assert(!strcmp(visible_title, "Restore share"));
    tap(140, 291);
    tap(215, 442);
    assert(!strcmp(visible_title, "Join repair"));
    save_frame("38-repair-join");
    ns_text join;
    assert(ns_threshold_output(custody[0], 0, &join) == NS_OK && join.len < sizeof(setup));
    memcpy(setup, join.data, join.len);
    setup[join.len] = 0;
    public_field(setup, "key", custody_keys[0]);
    assert(custody_collect() == 1 && scanning);
    char repair[1536];
    n = snprintf(repair, sizeof(repair),
                 "{\"type\":\"nsealr_repair\",\"session\":\"%064u\",\"group\":\"%.*s\","
                 "\"descriptor\":\"%s\",\"members\":[{\"id\":1,\"key\":\"%s\"},"
                 "{\"id\":2,\"key\":\"%s\"},{\"id\":3,\"key\":\"%s\"}],"
                 "\"participant\":%u,\"replacement\":\"%s\"}",
                 3u, 64, fingerprint, descriptor, sorted[0], sorted[1], sorted[2],
                 (unsigned)lost_member, custody_keys[0]);
    assert(n > 0 && (size_t)n < sizeof(repair));
    for (unsigned i = 0; i < 3; i++) {
        custody_feed(i, (const uint8_t *)repair, (size_t)n);
        if (i)
            peer_approve(i);
    }
    save_frame("39-repair-review");
    finish_visible_review();
    assert(custody_collect() == 2);
    custody_route(2);
    assert(custody_collect() == 2);
    custody_route(2);
    assert(ns_threshold_output_count(custody[0]) == 3);
    save_frame("40-repair-acknowledgements");
    assert(custody_collect() == 3);
    assert(!strcmp(visible_title, "Share restored"));
    custody_route(2);
    assert(custody_collect() == 2);
    for (unsigned i = 0; i < 3; i++) {
        uint8_t repaired_key[64], repaired_group[64];
        uint32_t member;
        assert(ns_public_key(custody[i], 0, repaired_key, sizeof(repaired_key), &written) ==
                   NS_OK &&
               !memcmp(group_key, repaired_key, 64));
        assert(ns_threshold_info(custody[i], repaired_group, &member) == NS_OK);
        if (!i) {
            assert(member == lost_member);
            memcpy(fingerprint, repaired_group, 64);
        } else
            assert(!memcmp(fingerprint, repaired_group, 64));
    }
    save_frame("41-repair-complete");
    tap(140, 291);
    /* The replacement can sign with either surviving share. Each request still
     * crosses the actual device scanner, reader, consent and outgoing QR. */
    for (unsigned helper = 1; helper < 3; helper++) {
        memcpy(members[0], custody_keys[0], 65);
        memcpy(members[1], custody_keys[helper], 65);
        qsort(members, 2, sizeof(members[0]), public_key_order);
        n = snprintf(request, sizeof(request),
                     "{\"type\":\"nsealr_sign\",\"id\":\"repaired-native\",\"session\":\"%"
                     "064u\","
                     "\"members\":[\"%s\",\"%s\"],\"event\":\"{\\\"pubkey\\\":\\\"%.*s\\\","
                     "\\\"created_at\\\":1794211200,\\\"kind\\\":1,\\\"tags\\\":[],"
                     "\\\"content\\\":\\\"Repaired share, same Nostr identity.\\\"}\"}",
                     3u + helper, members[0], members[1], 64, group_key);
        assert(n > 0 && (size_t)n < sizeof(request));
        tap(140, 175);
        custody_feed(0, (uint8_t *)request, (size_t)n);
        custody_feed(helper, (uint8_t *)request, (size_t)n);
        peer_approve(helper);
        finish_visible_review();
        assert(custody_collect() == 2);
        custody_route(2);
        assert(custody_collect() == 2);
        custody_route(2);
        assert(custody_collect() == 2);
        assert(!strcmp(custody_packets[0], custody_packets[1]));
        assert(strstr(custody_packets[0], "Repaired share, same Nostr identity."));
    }
    clear_loaded();
    assert(unlink(test_share_path) == 0);
    assert(platform_share_load(saved, sizeof(saved), &saved_len) == SHARE_FILE_MISSING);
    int fd = open(test_share_path, O_WRONLY | O_CREAT | O_EXCL, 0600);
    assert(fd >= 0 && ftruncate(fd, NS_THRESHOLD_MAX_BACKUP + 1) == 0 && close(fd) == 0);
    assert(platform_share_load(saved, sizeof(saved), &saved_len) == SHARE_FILE_INVALID);
    assert(saved_len == 0);
    for (size_t i = 0; i < sizeof(saved); i++)
        assert(saved[i] == 0);
    assert(unlink(test_share_path) == 0);
    test_media_available = false;
    for (unsigned i = 1; i < 3; i++)
        ns_deinit(custody[i]);
    platform_wipe(custody_backups, sizeof(custody_backups));
    testing = false;
    puts("PASS: real 3-device setup, all packets, animated share "
         "backup/check/recovery, "
         "rendered group consent and 2-device signing through actual UI input");
    puts("PASS: deliberate lost-share repair, all three final packets, stable "
         "member/npub and "
         "signing with either surviving share through actual UI input");
    puts("PASS: deliberate share-file save/read-back/restore, absent media, no "
         "overwrite, "
         "missing/oversize rejection and cleared error buffers (native "
         "filesystem)");
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
        signer_flow_test();
    } else if (argc == 3 && !strcmp(argv[1], "--render")) {
        render_dir = argv[2];
        flow_test();
        threshold_flow_test();
        signer_flow_test();
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
