#ifndef NSEALR_UI_H
#define NSEALR_UI_H
#include <lvgl.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

typedef enum {
    UI_HOME,
    UI_MENU,
    UI_INPUT,
    UI_WORD_ENTRY,
    UI_WORD_REVIEW,
    UI_READER,
    UI_CONFIRM,
    UI_SCAN,
    UI_QR,
    UI_SECRET,
    UI_NOTICE
} ui_screen;
enum {
    UI_BACK = 256,
    UI_NEXT,
    UI_CANCEL,
    UI_LOCK,
    UI_DONE,
    UI_READER_END,
    UI_KEY_BACKSPACE,
    UI_KEY_SPACE,
    UI_KEY_MODE,
    UI_KEY_CASE,
    UI_WORD_FIRST,
    UI_WORD_SECOND,
    UI_WORD_MORE,
    UI_WORD_PREVIOUS,
    UI_WORD_EDIT0,
    UI_WORD_EDIT1,
    UI_WORD_EDIT2,
    UI_WORD_EDIT3,
    UI_KEY_CLEAR,
    UI_KEY_SCAN
};
typedef struct {
    const char *label;
    unsigned action;
} ui_choice;
typedef struct {
    ui_screen screen;
    const char *title, *subtitle, *body;
    const ui_choice *choices;
    size_t choice_count;
    const char *left_label, *right_label;
    const char *aux_label, *header_label;
    unsigned aux_action, header_action;
    unsigned left_action, right_action;
    bool loaded, right_enabled, keyboard_upper, quiz;
    unsigned keyboard_page, word_choices;
    size_t input_length;
    unsigned progress, total;
    const uint8_t *qr;
    size_t qr_length;
} ui_view;
typedef void (*ui_action_cb)(unsigned action, void *context);
void ui_show(const ui_view *, ui_action_cb, void *);
void ui_set_input_length(size_t length);
void ui_enable_next(void);
lv_obj_t *ui_reader(void);
/* Escapes unsupported codepoints and controls; never silently drops bytes. */
bool ui_escape_text(const uint8_t *, size_t, char *, size_t, size_t *);
#endif
