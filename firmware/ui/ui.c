#include "ui.h"
#include "fonts/fonts.h"
#include <stdio.h>
#include <string.h>

#define BG 0x07060D
#define PANEL 0x0F0C17
#define FG 0xECE6F7
#define MUTED 0xB3A8C5
#define BORDER 0x251D38
#define ACCENT 0xA050FF
#define SOFT 0xC4A5FF

static ui_action_cb action_callback;
static void *action_context;
static lv_obj_t *reader, *input_count, *next_button;
static unsigned generation, pressed_generation;

static lv_obj_t *box(lv_obj_t *parent, int x, int y, int w, int h, uint32_t color) {
    lv_obj_t *o = lv_obj_create(parent);
    lv_obj_remove_style_all(o);
    lv_obj_set_pos(o, x, y);
    lv_obj_set_size(o, w, h);
    lv_obj_set_scrollable(o, false);
    lv_obj_set_style_bg_color(o, lv_color_hex(color), 0);
    lv_obj_set_style_bg_opa(o, LV_OPA_COVER, 0);
    lv_obj_set_style_radius(o, 10, 0);
    return o;
}
static lv_obj_t *text(lv_obj_t *parent, int x, int y, int w, const char *s, const lv_font_t *font,
                      uint32_t color) {
    lv_obj_t *o = lv_label_create(parent);
    lv_obj_set_pos(o, x, y);
    lv_obj_set_width(o, w);
    lv_obj_set_style_text_font(o, font, 0);
    lv_obj_set_style_text_color(o, lv_color_hex(color), 0);
    lv_obj_set_style_text_line_space(o, 4, 0);
    lv_label_set_long_mode(o, LV_LABEL_LONG_WRAP);
    lv_label_set_text(o, s ? s : "");
    return o;
}
static void event(lv_event_t *e) {
    if (lv_event_get_code(e) == LV_EVENT_PRESSED)
        pressed_generation = generation;
    if (lv_event_get_code(e) == LV_EVENT_CLICKED && pressed_generation == generation &&
        action_callback)
        action_callback((unsigned)(uintptr_t)lv_event_get_user_data(e), action_context);
}
static lv_obj_t *button(lv_obj_t *parent, int x, int y, int w, int h, const char *s,
                        unsigned action, bool primary) {
    lv_obj_t *o = lv_button_create(parent);
    lv_obj_remove_style_all(o);
    lv_obj_set_pos(o, x, y);
    lv_obj_set_size(o, w, h);
    lv_obj_set_style_radius(o, 8, 0);
    lv_obj_set_style_bg_opa(o, LV_OPA_COVER, 0);
    lv_obj_set_style_bg_color(o, lv_color_hex(primary ? ACCENT : PANEL), 0);
    lv_obj_set_style_bg_color(o, lv_color_hex(primary ? 0x7F36CF : BORDER), LV_STATE_PRESSED);
    lv_obj_set_style_bg_opa(o, LV_OPA_40, LV_STATE_DISABLED);
    lv_obj_t *caption = text(o, 0, 0, w - 10, s, &font_body16, FG);
    lv_obj_set_style_text_align(caption, LV_TEXT_ALIGN_CENTER, 0);
    lv_obj_center(caption);
    lv_obj_add_event_cb(o, event, LV_EVENT_ALL, (void *)(uintptr_t)action);
    return o;
}
static void reader_event(lv_event_t *e) {
    lv_obj_t *o = lv_event_get_target_obj(e);
    if (lv_obj_get_scroll_bottom(o) <= 1 && action_callback)
        action_callback(UI_READER_END, action_context);
}
static void footer(lv_obj_t *root, const ui_view *v) {
    box(root, 0, 405, 320, 75, BG);
    if (v->left_label)
        button(root, 16, 420, v->right_label ? 100 : 288, 48, v->left_label, v->left_action, false);
    if (v->right_label) {
        lv_obj_t *o = button(root, v->left_label ? 124 : 16, 420, v->left_label ? 180 : 288, 48,
                             v->right_label, v->right_action, true);
        next_button = o;
        lv_obj_set_state(o, LV_STATE_DISABLED, !v->right_enabled);
    }
}
static void keyboard(lv_obj_t *root, const ui_view *v) {
    static const char letters[] = "abcdefghijklmnopqrstuvwxyz.,-@";
    static const char symbols[] = "0123456789!#$%&()*+/:;=?[]_{}<>";
    static const char extra[] = "\"'\\^`|~@.,-:";
    const char *keys = v->keyboard_page == 2 ? extra : v->keyboard_page == 1 ? symbols : letters;
    input_count = text(root, 16, 105, 288, "", &font_body16, MUTED);
    if (v->body)
        lv_label_set_text(input_count, v->body);
    else
        ui_set_input_length(v->input_length);
    for (unsigned i = 0; i < strlen(keys); i++) {
        char c = keys[i];
        if (v->keyboard_upper && c >= 'a' && c <= 'z')
            c = (char)(c - 'a' + 'A');
        char label[2] = {c, 0};
        button(root, 16 + (i % 6) * 49, 174 + (i / 6) * 44, 43, 40, label, (unsigned char)c, false);
    }
    button(root, 16, 128, 68, 38,
           v->keyboard_page == 2   ? "ABC"
           : v->keyboard_page == 1 ? "More"
                                   : "123",
           UI_KEY_MODE, false);
    button(root, 91, 128, 65, 38, v->keyboard_upper ? "abc" : "ABC", UI_KEY_CASE, false);
    button(root, 163, 128, 65, 38, "Space", UI_KEY_SPACE, false);
    button(root, 235, 128, 69, 38, "Erase", UI_KEY_BACKSPACE, false);
}
void ui_show(const ui_view *v, ui_action_cb callback, void *context) {
    action_callback = callback;
    action_context = context;
    generation++;
    pressed_generation = 0;
    reader = NULL;
    input_count = NULL;
    next_button = NULL;
    lv_obj_t *root = lv_screen_active();
    lv_obj_clean(root);
    lv_obj_remove_style_all(root);
    lv_obj_set_scrollable(root, false);
    lv_obj_set_style_bg_color(root, lv_color_hex(BG), 0);
    lv_obj_set_style_bg_opa(root, LV_OPA_COVER, 0);
    text(root, 16, 15, 170, "nSealr", &font_title22, FG);
    if (v->loaded)
        button(root, 236, 8, 68, 36, "Lock", UI_LOCK, false);
    else
        text(root, 204, 23, 100, "OFFLINE", &font_body16, MUTED);
    box(root, 16, 51, 288, 1, BORDER);
    text(root, 16, 66, 288, v->title, &font_title26, FG);
    if (v->subtitle && v->screen != UI_INPUT && v->screen != UI_WORD_ENTRY)
        text(root, 16, 105, v->aux_label ? 192 : 288, v->subtitle, &font_body16, MUTED);
    if (v->aux_label)
        button(root, 214, 105, 90, 34, v->aux_label, v->aux_action, false);
    switch (v->screen) {
    case UI_HOME:
    case UI_MENU: {
        lv_obj_t *list = box(root, 16, 150, 288, 251, BG);
        lv_obj_set_scrollable(list, true);
        lv_obj_set_scroll_dir(list, LV_DIR_VER);
        for (size_t i = 0; i < v->choice_count; i++)
            button(list, 0, (int)i * 58, 288, 50, v->choices[i].label, v->choices[i].action,
                   i == 0);
        break;
    }
    case UI_INPUT:
        keyboard(root, v);
        break;
    case UI_WORD_ENTRY: {
        for (unsigned i = 0; i < v->word_choices; i++) {
            lv_obj_t *choice = button(root, 16, 140 + (int)i * 44, 288, 44, "",
                                      i ? UI_WORD_SECOND : UI_WORD_FIRST, false);
            lv_obj_set_style_bg_color(choice, lv_color_hex(BG), 0);
            lv_obj_set_style_border_width(choice, 1, 0);
            lv_obj_set_style_border_color(choice, lv_color_hex(BORDER), 0);
            text(choice, 236, 11, 46, "Use", &font_body16, SOFT);
        }
        if (!v->word_choices)
            text(root, 32, 154, 256, "Type the first letters.\nTap a matching word.", &font_body16,
                 MUTED);
        static const char alphabet[] = "abcdefghijklmnopqrstuvwxyz";
        for (unsigned i = 0; i < 26; i++) {
            char label[2] = {alphabet[i], 0};
            button(root, 16 + (i % 7) * 42, 244 + (i / 7) * 39, 38, 36, label,
                   (unsigned char)alphabet[i], false);
        }
        button(root, 226, 361, 38, 36, "Del", UI_KEY_BACKSPACE, false);
        button(root, 268, 361, 38, 36, "Clr", UI_KEY_CLEAR, false);
        break;
    }
    case UI_WORD_REVIEW:
        for (unsigned i = 0; i < v->word_choices; i++) {
            lv_obj_t *choice =
                button(root, 16, 140 + (int)i * 56, 288, 44, "", UI_WORD_EDIT0 + i, false);
            lv_obj_set_style_bg_color(choice, lv_color_hex(BG), 0);
            lv_obj_set_style_border_width(choice, 1, 0);
            lv_obj_set_style_border_color(choice, lv_color_hex(BORDER), 0);
            text(choice, 236, 11, 46, v->quiz ? "Use" : "Edit", &font_body16, SOFT);
        }
        break;
    case UI_READER:
        reader = box(root, 16, 146, 288, 252, PANEL);
        lv_obj_set_scrollable(reader, true);
        lv_obj_set_scroll_dir(reader, LV_DIR_VER);
        lv_obj_set_scrollbar_mode(reader, LV_SCROLLBAR_MODE_ON);
        lv_obj_set_style_pad_all(reader, 14, 0);
        lv_obj_set_style_width(reader, 3, LV_PART_SCROLLBAR);
        lv_obj_set_style_bg_color(reader, lv_color_hex(SOFT), LV_PART_SCROLLBAR);
        lv_obj_set_style_bg_opa(reader, LV_OPA_COVER, LV_PART_SCROLLBAR);
        text(reader, 0, 0, 252, v->body, &font_body18, FG);
        lv_obj_add_event_cb(reader, reader_event, LV_EVENT_SCROLL, NULL);
        break;
    case UI_CONFIRM:
    case UI_NOTICE: {
        lv_obj_t *card = box(root, 16, 158, 288, 230, PANEL);
        text(card, 16, 16, 256, v->body, &font_body18, FG);
        break;
    }
    case UI_SCAN: {
        lv_obj_t *card = box(root, 32, 166, 256, 194, PANEL);
        text(card, 20, 68, 216, "Hold the QR steady", &font_body18, FG);
        char progress[48];
        snprintf(progress, sizeof(progress), v->total ? "Received %u of %u" : "Ready to scan",
                 v->progress, v->total);
        text(root, 16, 375, 288, progress, &font_body16, MUTED);
        break;
    }
    case UI_QR: {
        lv_obj_t *qr = lv_qrcode_create(root);
        lv_qrcode_set_size(qr, 250);
        lv_qrcode_set_dark_color(qr, lv_color_black());
        lv_qrcode_set_light_color(qr, lv_color_white());
        lv_qrcode_set_quiet_zone(qr, true);
        lv_obj_set_pos(qr, 35, 148);
        if (!v->qr || lv_qrcode_update(qr, v->qr, (uint32_t)v->qr_length) != LV_RESULT_OK) {
            lv_obj_delete(qr);
            text(root, 16, 210, 288, "Cannot display this QR", &font_body18, FG);
        }
        break;
    }
    case UI_SECRET:
        break; /* Direct, acknowledged secret raster is drawn by the board. */
    }
    footer(root, v);
}
void ui_set_input_length(size_t length) {
    if (input_count) {
        char s[48];
        snprintf(s, sizeof(s), "%zu characters entered", length);
        lv_label_set_text(input_count, s);
    }
}
void ui_enable_next(void) {
    if (next_button)
        lv_obj_set_state(next_button, LV_STATE_DISABLED, false);
}
lv_obj_t *ui_reader(void) { return reader; }

bool ui_escape_text(const uint8_t *in, size_t n, char *out, size_t cap, size_t *written) {
    if (!out || !cap || !written || (!in && n))
        return false;
    size_t at = 0;
    for (size_t i = 0; i < n;) {
        uint32_t cp = in[i++];
        unsigned extra = 0;
        uint32_t minimum = 0;
        if (cp >= 0x80) {
            if (cp >= 0xC2 && cp <= 0xDF) {
                extra = 1;
                minimum = 0x80;
                cp &= 31;
            } else if (cp >= 0xE0 && cp <= 0xEF) {
                extra = 2;
                minimum = 0x800;
                cp &= 15;
            } else if (cp >= 0xF0 && cp <= 0xF4) {
                extra = 3;
                minimum = 0x10000;
                cp &= 7;
            } else
                return false;
            if (extra > n - i)
                return false;
            while (extra--) {
                uint8_t b = in[i++];
                if ((b & 0xC0) != 0x80)
                    return false;
                cp = (cp << 6) | (b & 63);
            }
            if (cp < minimum || cp > 0x10FFFF || (cp >= 0xD800 && cp <= 0xDFFF))
                return false;
        }
        char escaped[16];
        size_t k;
        if (cp == '\\') {
            escaped[0] = '\\';
            escaped[1] = '\\';
            k = 2;
        } else if (cp == '\n' || (cp >= 32 && cp <= 126)) {
            escaped[0] = (char)cp;
            k = 1;
        } else {
            int count = snprintf(escaped, sizeof(escaped), "\\u{%lx}", (unsigned long)cp);
            if (count < 0)
                return false;
            k = (size_t)count;
        }
        if (k >= cap - at)
            return false;
        memcpy(out + at, escaped, k);
        at += k;
    }
    out[at] = 0;
    *written = at;
    return true;
}
