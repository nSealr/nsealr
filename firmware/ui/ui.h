#ifndef NSEALR_UI_H
#define NSEALR_UI_H

#include <stdbool.h>
#include <lvgl.h>

/* Presentation only. Current layouts use public fixture semantics; they are not
 * a production review adapter. All strings are public display data, never custody
 * secrets. The eventual owner retains authorization and the immutable request. */
typedef enum {
    UI_HOME, UI_IDENTITY, UI_IDENTITY_CONFIRM, UI_SCAN, UI_REVIEW,
    UI_CONTENT, UI_DETAILS, UI_DECISION, UI_RESULT, UI_SETTINGS, UI_UNSUPPORTED,
    UI_CREATE_IDENTITY
} ui_screen;

typedef enum {
    UI_CREATE, UI_IMPORT, UI_USE_EXAMPLE, UI_SCAN_REQUEST, UI_LOAD_REQUEST,
    UI_READ_CONTENT, UI_OPEN_DETAILS, UI_CONTINUE, UI_BACK, UI_REJECT,
    UI_CONFIRM, UI_ALLOW_PARTIAL, UI_DONE, UI_OPEN_SETTINGS, UI_LOCK, UI_CONTENT_END
} ui_action;

typedef struct {
    ui_screen screen;
    bool preview;
    bool identity_loaded;
    bool content_seen;
    const char *identity;
    const char *public_key;
    const char *content;
    const char *details;
    const char *result_qr;
} ui_view;

typedef void (*ui_action_cb)(ui_action action, void *context);

void ui_show(const ui_view *view, ui_action_cb on_action, void *context);
/* Exposed for the input adapter and preview tests, not as signing authority. */
lv_obj_t *ui_content_reader(void);

#endif
