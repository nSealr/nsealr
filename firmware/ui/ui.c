#include "ui.h"
#include <stdint.h>
#include <string.h>

#define BG 0x0E141B
#define CARD 0x1C2631
#define TEXT 0xF3F5F7
#define MUTED 0xA9B5C2
#define ACCENT 0xD7F29A
#define WARN 0xFFD08A
#define LINE 0x34404D

static ui_action_cb callback;
static void *callback_context;
static lv_obj_t *reader;

static lv_obj_t *box(lv_obj_t *parent, int x, int y, int w, int h, uint32_t color)
{
    lv_obj_t *obj = lv_obj_create(parent);
    lv_obj_remove_style_all(obj);
    lv_obj_set_pos(obj, x, y);
    lv_obj_set_size(obj, w, h);
    lv_obj_set_style_bg_color(obj, lv_color_hex(color), 0);
    lv_obj_set_style_bg_opa(obj, LV_OPA_COVER, 0);
    lv_obj_set_scrollable(obj, false);
    return obj;
}

static lv_obj_t *label(lv_obj_t *parent, int x, int y, int w, const char *text,
                       const lv_font_t *font, uint32_t color)
{
    lv_obj_t *obj = lv_label_create(parent);
    lv_obj_set_pos(obj, x, y);
    lv_obj_set_width(obj, w);
    lv_obj_set_style_text_font(obj, font, 0);
    lv_obj_set_style_text_color(obj, lv_color_hex(color), 0);
    lv_obj_set_style_text_line_space(obj, 4, 0);
    lv_label_set_long_mode(obj, LV_LABEL_LONG_WRAP);
    lv_label_set_text(obj, text);
    return obj;
}

static void activated(lv_event_t *event)
{
    ui_action action = (ui_action)(uintptr_t)lv_event_get_user_data(event);
    /* A click is an intent for the owner, never authorization in this renderer. */
    if(callback) callback(action, callback_context);
}

static lv_obj_t *button(lv_obj_t *parent, int x, int y, int w, const char *text,
                        ui_action action, bool primary)
{
    lv_obj_t *obj = lv_button_create(parent);
    lv_obj_remove_style_all(obj);
    lv_obj_set_pos(obj, x, y);
    lv_obj_set_size(obj, w, 48);
    lv_obj_set_style_radius(obj, 12, 0);
    lv_obj_set_style_bg_opa(obj, LV_OPA_COVER, 0);
    lv_obj_set_style_bg_color(obj, lv_color_hex(primary ? ACCENT : CARD), 0);
    lv_obj_set_style_bg_color(obj, lv_color_hex(primary ? 0xB6CE7D : LINE), LV_STATE_PRESSED);
    lv_obj_t *caption = label(obj, 0, 0, w - 16, text, &lv_font_montserrat_16,
                             primary ? BG : TEXT);
    lv_obj_set_style_text_align(caption, LV_TEXT_ALIGN_CENTER, 0);
    lv_obj_center(caption);
    lv_obj_add_event_cb(obj, activated, LV_EVENT_CLICKED, (void *)(uintptr_t)action);
    return obj;
}

static void footer(lv_obj_t *root, const char *left, ui_action left_action,
                   const char *right, ui_action right_action)
{
    box(root, 0, 403, 320, 77, BG);
    button(root, 20, 412, 104, left, left_action, false);
    button(root, 132, 412, 168, right, right_action, true);
}

static void heading(lv_obj_t *root, const char *eyebrow, const char *title,
                    const char *subtitle)
{
    label(root, 20, 58, 280, eyebrow, &lv_font_montserrat_12, ACCENT);
    label(root, 20, 82, 280, title, &lv_font_montserrat_28, TEXT);
    if(subtitle) label(root, 20, 124, 280, subtitle, &lv_font_montserrat_14, MUTED);
}

static void card_text(lv_obj_t *root, int y, int h, const char *eyebrow, const char *text)
{
    lv_obj_t *card = box(root, 20, y, 280, h, CARD);
    lv_obj_set_style_radius(card, 14, 0);
    label(card, 16, 14, 248, eyebrow, &lv_font_montserrat_12, MUTED);
    label(card, 16, 37, 248, text, &lv_font_montserrat_16, TEXT);
}

static void home(lv_obj_t *root, const ui_view *view)
{
    heading(root, view->identity_loaded ? "IDENTITY" : "OFFLINE SIGNER",
            view->identity_loaded ? "Ready to review" : "Your identity.\nYour control.", NULL);
    if(view->identity_loaded) {
        card_text(root, 150, 112, "PUBLIC EXAMPLE", view->identity);
        label(root, 20, 286, 280, "Scan a request from your companion. Review it here before deciding.",
              &lv_font_montserrat_16, MUTED);
        button(root, 20, 356, 280, "Scan a request", UI_SCAN_REQUEST, true);
        button(root, 20, 412, 280, "Identity & session", UI_OPEN_SETTINGS, false);
    } else {
        label(root, 20, 170, 280, "Keep your Nostr key offline.\nReview requests on your device.",
              &lv_font_montserrat_16, MUTED);
        card_text(root, 246, 82, "SESSION", "No identity loaded");
        button(root, 20, 356, 280, "Create identity", UI_CREATE, true);
        button(root, 20, 412, 280, "Import identity", UI_IMPORT, false);
    }
}

static void identity(lv_obj_t *root, bool create)
{
    heading(root, "IDENTITY  /  1 OF 2", create ? "Create an identity" : "Bring your identity",
            create ? "Choose the length of your recovery words." : "Choose how to recover your Nostr key.");
    button(root, 20, 184, 280, create ? "12 recovery words" : "Recovery words", UI_USE_EXAMPLE, false);
    button(root, 20, 242, 280, create ? "24 recovery words" : "Private key (nsec)", UI_USE_EXAMPLE, false);
    if(!create) button(root, 20, 300, 280, "Scan a backup", UI_USE_EXAMPLE, false);
    label(root, 20, 364, 280, create ? "Preview opens public sample data.\nNo recovery words are generated."
                                  : "Preview opens public sample data.\nNo secret entry is connected.",
          &lv_font_montserrat_12, MUTED);
    button(root, 20, 412, 280, "Back", UI_BACK, false);
}

static void identity_confirm(lv_obj_t *root, const ui_view *view)
{
    heading(root, "IDENTITY  /  2 OF 2", "Check the identity", "Compare the full public key with your backup.");
    card_text(root, 178, 72, "PUBLIC EXAMPLE", "NIP-19 reference identity");
    label(root, 24, 276, 272, view->public_key, &lv_font_montserrat_14, TEXT);
    label(root, 20, 371, 280, "Public data only. No key was imported.", &lv_font_montserrat_12, MUTED);
    footer(root, "Back", UI_BACK, "Use example", UI_USE_EXAMPLE);
}

static void scanner(lv_obj_t *root)
{
    heading(root, "REQUEST", "Scan to review", "Point the camera at your companion's QR.");
    lv_obj_t *camera = box(root, 44, 176, 232, 176, CARD);
    lv_obj_set_style_radius(camera, 16, 0);
    lv_obj_set_style_border_width(camera, 2, 0);
    lv_obj_set_style_border_color(camera, lv_color_hex(LINE), 0);
    label(camera, 0, 33, 232, LV_SYMBOL_IMAGE, &lv_font_montserrat_28, ACCENT);
    lv_obj_set_style_text_align(lv_obj_get_child(camera, 0), LV_TEXT_ALIGN_CENTER, 0);
    lv_obj_t *hint = label(camera, 14, 84, 204, "Camera preview\nnot connected", &lv_font_montserrat_16, MUTED);
    lv_obj_set_style_text_align(hint, LV_TEXT_ALIGN_CENTER, 0);
    label(root, 20, 373, 280, "Load a public request to explore the flow.", &lv_font_montserrat_12, MUTED);
    footer(root, "Cancel", UI_BACK, "Load example", UI_LOAD_REQUEST);
}

static void review(lv_obj_t *root, const ui_view *view)
{
    heading(root, "PUBLIC NOTE", "Publish this post?", "Public example identity  /  kind 1");
    lv_obj_t *card = box(root, 20, 166, 280, 134, CARD);
    lv_obj_set_style_radius(card, 14, 0);
    lv_obj_t *text = label(card, 16, 15, 248, view->content, &lv_font_montserrat_18, TEXT);
    lv_obj_set_height(text, 82);
    label(root, 20, 312, 280, view->content_seen ? "Reached the end of the text." : "Preview only. More text is included.",
          &lv_font_montserrat_12, view->content_seen ? MUTED : WARN);
    button(root, 20, 343, 136, "Read full text", UI_READ_CONTENT, false);
    button(root, 164, 343, 136, "Exact details", UI_OPEN_DETAILS, false);
    footer(root, "Reject", UI_REJECT, "Continue", UI_CONTINUE);
}

static void content_scrolled(lv_event_t *event)
{
    lv_obj_t *obj = lv_event_get_target_obj(event);
    if(lv_obj_get_scroll_bottom(obj) <= 1 && callback)
        callback(UI_CONTENT_END, callback_context);
}

static void scroll_view(lv_obj_t *root, const ui_view *view, bool details)
{
    heading(root, details ? "EXACT SIGNED DATA" : "POST CONTENT",
            details ? "Request details" : "Read the full text", NULL);
    reader = box(root, 20, 132, 280, 266, CARD);
    lv_obj_set_style_radius(reader, 12, 0);
    lv_obj_set_scrollable(reader, true);
    lv_obj_set_scroll_dir(reader, LV_DIR_VER);
    lv_obj_set_scrollbar_mode(reader, LV_SCROLLBAR_MODE_ON);
    lv_obj_set_style_pad_all(reader, 16, 0);
    lv_obj_set_style_bg_color(reader, lv_color_hex(ACCENT), LV_PART_SCROLLBAR);
    lv_obj_set_style_bg_opa(reader, LV_OPA_COVER, LV_PART_SCROLLBAR);
    lv_obj_set_style_width(reader, 3, LV_PART_SCROLLBAR);
    lv_obj_set_style_radius(reader, 2, LV_PART_SCROLLBAR);
    label(reader, 0, 0, 244, details ? view->details : view->content,
          details ? &lv_font_montserrat_14 : &lv_font_montserrat_18, TEXT);
    if(!details) lv_obj_add_event_cb(reader, content_scrolled, LV_EVENT_SCROLL, NULL);
    button(root, 20, 412, 280, "Back to review", UI_BACK, false);
}

static void decision(lv_obj_t *root, const ui_view *view)
{
    heading(root, "YOUR DECISION", view->content_seen ? "Confirm this request" : "Text not fully shown", NULL);
    card_text(root, 148, 100, "ACTION", "Publish a public note\nwith the example identity");
    label(root, 20, 272, 280,
          view->content_seen ? "This preview does not sign. Continue to see the result layout."
                             : "You have not viewed all the text. Unseen words could change what you are publishing.",
          &lv_font_montserrat_16, view->content_seen ? MUTED : WARN);
    if(!view->content_seen) button(root, 20, 345, 280, "Read full text", UI_READ_CONTENT, false);
    footer(root, "Back", UI_BACK, view->content_seen ? "Preview result" : "Preview anyway",
           view->content_seen ? UI_CONFIRM : UI_ALLOW_PARTIAL);
}

static void result(lv_obj_t *root, const ui_view *view)
{
    heading(root, "RESULT PREVIEW", "Return this QR", "Public example QR. No event was signed.");
    lv_obj_t *qr = lv_qrcode_create(root);
    lv_qrcode_set_size(qr, 212);
    lv_qrcode_set_dark_color(qr, lv_color_hex(0x0E141B));
    lv_qrcode_set_light_color(qr, lv_color_white());
    lv_qrcode_set_quiet_zone(qr, true);
    lv_obj_set_pos(qr, 54, 174);
    if(lv_qrcode_update(qr, view->result_qr, (uint32_t)strlen(view->result_qr)) != LV_RESULT_OK) {
        lv_obj_delete(qr);
        card_text(root, 200, 112, "QR UNAVAILABLE", "Public preview encoding failed.");
    }
    button(root, 20, 412, 280, "Done", UI_DONE, true);
}

static void settings(lv_obj_t *root, const ui_view *view)
{
    heading(root, "SESSION", "Your identity", "Public sample; no custody session is active.");
    card_text(root, 174, 90, "IDENTITY", view->identity);
    label(root, 20, 286, 280, view->public_key, &lv_font_montserrat_14, TEXT);
    footer(root, "Back", UI_BACK, "Leave example", UI_LOCK);
}

static void unsupported(lv_obj_t *root)
{
    heading(root, "REQUEST STOPPED", "Not supported yet", NULL);
    card_text(root, 150, 112, "LONG-FORM ARTICLE", "This signer does not support\nthis kind of request.");
    label(root, 20, 288, 280, "Nothing was signed. Return to your companion and choose a supported action.",
          &lv_font_montserrat_16, MUTED);
    button(root, 20, 412, 280, "Return home", UI_DONE, true);
}

void ui_show(const ui_view *view, ui_action_cb on_action, void *context)
{
    callback = on_action;
    callback_context = context;
    reader = NULL;
    lv_obj_t *root = lv_screen_active();
    lv_obj_clean(root);
    lv_obj_remove_style_all(root);
    lv_obj_set_style_bg_color(root, lv_color_hex(BG), 0);
    lv_obj_set_style_bg_opa(root, LV_OPA_COVER, 0);
    lv_obj_set_scrollable(root, false);
    label(root, 20, 17, 110, "nSealr", &lv_font_montserrat_18, TEXT);
    lv_obj_t *badge = label(root, 170, 21, 130, view->preview ? "PUBLIC PREVIEW" : "OFFLINE SIGNER",
                            &lv_font_montserrat_12, MUTED);
    lv_obj_set_style_text_align(badge, LV_TEXT_ALIGN_RIGHT, 0);
    box(root, 20, 44, 280, 1, LINE);
    switch(view->screen) {
        case UI_HOME: home(root, view); break;
        case UI_IDENTITY: identity(root, false); break;
        case UI_CREATE_IDENTITY: identity(root, true); break;
        case UI_IDENTITY_CONFIRM: identity_confirm(root, view); break;
        case UI_SCAN: scanner(root); break;
        case UI_REVIEW: review(root, view); break;
        case UI_CONTENT: scroll_view(root, view, false); break;
        case UI_DETAILS: scroll_view(root, view, true); break;
        case UI_DECISION: decision(root, view); break;
        case UI_RESULT: result(root, view); break;
        case UI_SETTINGS: settings(root, view); break;
        case UI_UNSUPPORTED: unsupported(root); break;
    }
}

lv_obj_t *ui_content_reader(void) { return reader; }
