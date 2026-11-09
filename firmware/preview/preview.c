#include "ui.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* NIP-19's published public-key example. No private keys or secret fixtures. */
static const char public_key[] =
    "npub180cvv07tjdrrgpa0j7j7tmnyl2yr6yr7l8j4s3evf6u64th6gkwsyjh6w6";
static const char content[] =
    "A quieter place to keep your keys. A clearer way to decide what you sign.\n\n"
    "Your Nostr identity should be yours to carry, recover and use. An offline "
    "signer separates your key from the computer that connects you to the world.\n\n"
    "That separation is useful only when the request is understandable. A hash "
    "cannot explain a post, a recipient or a permission. The device should show "
    "the action and let you inspect the exact text.\n\n"
    "This is public interface sample text. It is not a signed event and no "
    "private identity is loaded.\n\n"
    "End of post.";
static const char details[] =
    "ACTION\nPublic note\n\nKIND\n1\n\nAUTHOR\n"
    "3bf0c63fcb93463407af97a5e5ee64fa883d107ef9e558472c4eb9aaaefa459d\n\n"
    "CREATED_AT\n1794211200\n\nTAGS\n[]\n\n"
    "CONTENT\nThe complete text is available in Read full text.\n\n"
    "PREVIEW BOUNDARY\nThis data is not parsed, hashed or signed by a custody core. "
    "There is no approval token or signature behind these screens.";
static const char result_qr[] =
    "nostr:npub180cvv07tjdrrgpa0j7j7tmnyl2yr6yr7l8j4s3evf6u64th6gkwsyjh6w6";

static ui_view view = {
    .screen = UI_HOME, .preview = true, .identity = "NIP-19 example",
    .public_key = public_key, .content = content, .details = details, .result_qr = result_qr
};
static ui_screen return_to = UI_REVIEW;
static ui_screen identity_from = UI_IDENTITY;
static unsigned result_previews;
static uint32_t pixels[320 * 480];
static uint8_t rgb[320 * 480 * 3];
static lv_indev_t *pointer;
static lv_point_t point;
static bool pointer_down;

static void flush(lv_display_t *display, const lv_area_t *area, uint8_t *data)
{
    uint32_t *src = (uint32_t *)data;
    for(int y = area->y1; y <= area->y2; ++y) {
        for(int x = area->x1; x <= area->x2; ++x) {
            uint32_t pixel = *src++;
            size_t at = ((size_t)y * 320 + (size_t)x) * 3;
            rgb[at] = (uint8_t)(pixel >> 16);
            rgb[at + 1] = (uint8_t)(pixel >> 8);
            rgb[at + 2] = (uint8_t)pixel;
        }
    }
    lv_display_flush_ready(display);
}

static void pointer_read(lv_indev_t *indev, lv_indev_data_t *data)
{
    (void)indev;
    data->point = point;
    data->state = pointer_down ? LV_INDEV_STATE_PRESSED : LV_INDEV_STATE_RELEASED;
}

static void draw(void)
{
    lv_obj_update_layout(lv_screen_active());
    lv_tick_inc(40);
    lv_timer_handler();
    lv_refr_now(NULL);
}

static void action(ui_action event, void *context)
{
    (void)context;
    switch(event) {
        case UI_CREATE: view.screen = UI_CREATE_IDENTITY; identity_from = view.screen; break;
        case UI_IMPORT: view.screen = UI_IDENTITY; identity_from = view.screen; break;
        case UI_USE_EXAMPLE:
            if(view.screen == UI_IDENTITY || view.screen == UI_CREATE_IDENTITY) view.screen = UI_IDENTITY_CONFIRM;
            else { view.identity_loaded = true; view.screen = UI_HOME; }
            break;
        case UI_SCAN_REQUEST: view.screen = UI_SCAN; break;
        case UI_LOAD_REQUEST: view.screen = UI_REVIEW; view.content_seen = false; break;
        case UI_READ_CONTENT: return_to = view.screen; view.screen = UI_CONTENT; break;
        case UI_OPEN_DETAILS: return_to = view.screen; view.screen = UI_DETAILS; break;
        case UI_CONTINUE: view.screen = UI_DECISION; break;
        case UI_CONTENT_END: view.content_seen = true; return;
        case UI_BACK:
            switch(view.screen) {
                case UI_CONTENT: case UI_DETAILS: view.screen = return_to; break;
                case UI_DECISION: view.screen = UI_REVIEW; break;
                case UI_IDENTITY_CONFIRM: view.screen = identity_from; break;
                default: view.screen = UI_HOME; view.content_seen = false; break;
            }
            break;
        case UI_REJECT:
        case UI_DONE: view.screen = UI_HOME; view.content_seen = false; break;
        case UI_CONFIRM:
            if(!view.content_seen || view.screen != UI_DECISION) return;
            view.screen = UI_RESULT; ++result_previews; break;
        case UI_ALLOW_PARTIAL:
            if(view.screen != UI_DECISION) return;
            view.screen = UI_RESULT; ++result_previews; break;
        case UI_OPEN_SETTINGS: view.screen = UI_SETTINGS; break;
        case UI_LOCK:
            view.identity_loaded = false; view.content_seen = false; view.screen = UI_HOME; break;
    }
    ui_show(&view, action, NULL);
}

static void tap(int x, int y)
{
    point.x = x; point.y = y;
    pointer_down = true;
    lv_indev_read(pointer);
    lv_tick_inc(30);
    pointer_down = false;
    lv_indev_read(pointer);
    draw();
}

static void drag(int x, int y1, int y2)
{
    point.x = x; point.y = y1; pointer_down = true;
    lv_indev_read(pointer);
    for(int i = 1; i <= 12; ++i) {
        point.y = y1 + (y2 - y1) * i / 12;
        lv_tick_inc(30);
        lv_indev_read(pointer);
    }
    pointer_down = false;
    lv_indev_read(pointer);
    for(int i = 0; i < 15; ++i) { lv_tick_inc(40); lv_timer_handler(); }
    draw();
}

static void save(const char *path)
{
    draw();
    FILE *out = fopen(path, "wb");
    if(!out) { perror(path); exit(1); }
    fprintf(out, "P6\n320 480\n255\n");
    if(fwrite(rgb, 1, sizeof(rgb), out) != sizeof(rgb) || fclose(out) != 0) {
        fputs("Could not save the preview frame\n", stderr); exit(1);
    }
}

static void render_screen(const char *directory, const char *name, ui_screen screen)
{
    char path[2048];
    assert(snprintf(path, sizeof(path), "%s/%s.ppm", directory, name) < (int)sizeof(path));
    view.screen = screen;
    ui_show(&view, action, NULL);
    save(path);
}

static void navigation_test(void)
{
    view.screen = UI_HOME; view.identity_loaded = false; view.content_seen = false;
    ui_show(&view, action, NULL); draw();
    tap(160, 435); assert(view.screen == UI_IDENTITY);
    tap(150, 208); assert(view.screen == UI_IDENTITY_CONFIRM);
    tap(220, 435); assert(view.screen == UI_HOME && view.identity_loaded);
    tap(150, 379); assert(view.screen == UI_SCAN);
    tap(72, 435); assert(view.screen == UI_HOME && result_previews == 0);
    tap(150, 379); tap(220, 435); assert(view.screen == UI_REVIEW);
    tap(72, 435); assert(view.screen == UI_HOME && result_previews == 0);
    tap(150, 379); tap(220, 435); tap(220, 435);
    assert(view.screen == UI_DECISION && !view.content_seen);
    /* No normal confirmation path is accepted without reaching the reader end. */
    action(UI_CONFIRM, NULL); assert(view.screen == UI_DECISION && result_previews == 0);
    tap(72, 435); assert(view.screen == UI_REVIEW);
    tap(80, 367); assert(view.screen == UI_CONTENT && !view.content_seen);
    for(unsigned i = 0; i < 20 && !view.content_seen; ++i) drag(240, 370, 180);
    assert(view.content_seen && lv_obj_get_scroll_bottom(ui_content_reader()) <= 1);
    tap(160, 435); assert(view.screen == UI_REVIEW);
    tap(220, 367); assert(view.screen == UI_DETAILS);
    tap(160, 435); tap(220, 435); assert(view.screen == UI_DECISION);
    tap(220, 435); assert(view.screen == UI_RESULT && result_previews == 1);
    tap(160, 435); assert(view.screen == UI_HOME && !view.content_seen);
    tap(150, 379); tap(220, 435); tap(220, 435);
    assert(view.screen == UI_DECISION && !view.content_seen);
    tap(220, 435); assert(view.screen == UI_RESULT && result_previews == 2);
    tap(160, 435); tap(160, 435); assert(view.screen == UI_SETTINGS);
    tap(220, 435); assert(view.screen == UI_HOME && !view.identity_loaded);
    tap(160, 379); assert(view.screen == UI_CREATE_IDENTITY);
    tap(160, 208); assert(view.screen == UI_IDENTITY_CONFIRM);
    tap(72, 435); assert(view.screen == UI_CREATE_IDENTITY);
    tap(160, 435); assert(view.screen == UI_HOME && !view.identity_loaded);
    puts("PASS: actual LVGL pointer navigation, cancel/reject, full reader, partial confirmation, reset and leave-example");
}

int main(int argc, char **argv)
{
    lv_init();
    lv_display_t *display = lv_display_create(320, 480);
    lv_display_set_color_format(display, LV_COLOR_FORMAT_XRGB8888);
    lv_display_set_buffers(display, pixels, NULL, sizeof(pixels), LV_DISPLAY_RENDER_MODE_FULL);
    lv_display_set_flush_cb(display, flush);
    pointer = lv_indev_create();
    lv_indev_set_type(pointer, LV_INDEV_TYPE_POINTER);
    lv_indev_set_read_cb(pointer, pointer_read);
    ui_show(&view, action, NULL); draw();
    if(argc == 2 && strcmp(argv[1], "--test") == 0) {
        navigation_test();
    } else if(argc == 3 && strcmp(argv[1], "--render") == 0) {
        render_screen(argv[2], "01-home", UI_HOME);
        render_screen(argv[2], "02-identity", UI_IDENTITY);
        render_screen(argv[2], "03-identity-confirm", UI_IDENTITY_CONFIRM);
        view.identity_loaded = true;
        render_screen(argv[2], "04-ready", UI_HOME);
        render_screen(argv[2], "05-scan", UI_SCAN);
        render_screen(argv[2], "06-review", UI_REVIEW);
        render_screen(argv[2], "07-content", UI_CONTENT);
        render_screen(argv[2], "08-details", UI_DETAILS);
        render_screen(argv[2], "09-partial-review", UI_DECISION);
        render_screen(argv[2], "10-result", UI_RESULT);
        render_screen(argv[2], "11-session", UI_SETTINGS);
        render_screen(argv[2], "12-unsupported", UI_UNSUPPORTED);
        view.content_seen = true;
        render_screen(argv[2], "13-confirm-review", UI_DECISION);
        render_screen(argv[2], "14-create", UI_CREATE_IDENTITY);
        puts("Rendered 14 public-preview screens; no camera, custody or signatures.");
    } else if(argc == 3 && strcmp(argv[1], "--interactive") == 0) {
        char command[128];
        save(argv[2]); puts("ready"); fflush(stdout);
        while(fgets(command, sizeof(command), stdin)) {
            int x, y, end;
            if(sscanf(command, "tap %d %d", &x, &y) == 2 && x >= 0 && x < 320 && y >= 0 && y < 480) tap(x, y);
            else if(sscanf(command, "drag %d %d %d", &x, &y, &end) == 3 && x >= 0 && x < 320 && y >= 0 && y < 480 && end >= 0 && end < 480) drag(x, y, end);
            else if(strcmp(command, "quit\n") == 0) break;
            save(argv[2]); puts("ready"); fflush(stdout);
        }
    } else {
        fprintf(stderr, "Usage: %s --test | --render DIRECTORY | --interactive FRAME.ppm\n", argv[0]);
        return 2;
    }
    lv_deinit();
    return 0;
}
