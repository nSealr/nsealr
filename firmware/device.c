#include "device.h"
#include "backup_check.h"
#include "word_input.h"
#include <stdalign.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Identity/backup/input storage is static internal RAM on the target. */
static alignas(NS_CONTEXT_ALIGN) uint8_t core_storage[NS_CONTEXT_BYTES];
static ns_context *core = (ns_context *)core_storage;
static uint8_t source[512], passphrase[256], secret_page[136], entropy[32];
static char account_text[12], public_key[65], npub[65], message[256], caption[96], confirmation[64];
static uint8_t qr_frame[NS_MAX_FRAME];
static size_t source_len, passphrase_len, input_len, qr_length, secret_page_len;
static uint32_t source_kind, words, account, requested_account, backup_kind, backup_page;
static uint32_t review_index, review_flags, response_frame;
static int32_t response_error;
static uint64_t review_generation, deadline, last_frame;
static size_t private_offset;
static char *public_body;
static bool generating, backup_prompt, partial, reader_done, scanning, reading_details;
static bool keyboard_upper;
static unsigned keyboard_page;
static unsigned input_target;
static word_input word_draft;
static bool have_word_draft, editing_word;
static unsigned word_review_page;
static backup_check quiz;
static bool backup_checked, has_passphrase, response_paused, editing_account;
static uint8_t backup_expected[512];
static size_t backup_expected_len;
static alignas(64) uint8_t share_backup[NS_THRESHOLD_MAX_BACKUP];
static uint32_t threshold_packet;
static bool threshold_restoring;

static ui_view view;

enum {
    HOME,
    CREATE,
    IMPORT,
    ENTRY,
    WORD_COUNT,
    WORD_MORE_LENGTHS,
    WORD_ENTRY,
    WORD_REVIEW,
    WORD_INVALID,
    PASSPHRASE_REVIEW,
    PASSPHRASE_HELP,
    QUIZ,
    QUIZ_WRONG,
    BACKUP_GOOD,
    BACKUP_BAD,
    PUBLIC_TEXT,
    IDENTITY,
    PUBLIC_IDENTITY,
    SCAN,
    REVIEW,
    DETAILS,
    DECISION,
    PARTIAL,
    RESPONSE,
    RESPONSE_REASON,
    BACKUP,
    REVEAL_WORDS,
    REVEAL_NSEC,
    REVEAL_QR,
    BACKUP_OPTIONS,
    NSEC_REVIEW,
    GROUP_INTRO,
    REPAIR_INTRO,
    GROUP_READY,
    GROUP_RECORD,
    GROUP_QR,
    THRESHOLD_QR,
    SHARE_BACKUP,
    SHARE_QR_CONSENT,
    SHARE_SAVE_CONSENT,
    SHARE_RESTORE,
    SHARE_SAVED,
    SHARE_QR,
    NOTICE
};
static unsigned state, scan_target, notice_return = HOME;
static unsigned public_return = HOME, record_return = HOME;
enum {
    SCAN_REQUEST,
    SCAN_KEY,
    SCAN_BACKUP_CHECK,
    SCAN_THRESHOLD,
    SCAN_SHARE_IMPORT,
    SCAN_SHARE_CHECK,
    SCAN_PASSPHRASE
};
enum {
    A_CREATE = 1000,
    A_IMPORT,
    A_SCAN,
    A_PUBLIC,
    A_BACKUP,
    A_GEN12,
    A_GEN24,
    A_GEN_RAW,
    A_WORDS,
    A_NSEC,
    A_SECRET_QR,
    A_ADD_PASS,
    A_ACCOUNT_EDIT,
    A_USE,
    A_BACKUP_WORDS,
    A_BACKUP_NSEC,
    A_BACKUP_SEEDQR,
    A_BACKUP_COMPACT,
    A_DETAILS,
    A_RESUME_REVIEW,
    A_SKIP_TEXT,
    A_APPROVE,
    A_PARTIAL_APPROVE,
    A_PUBLIC_TEXT,
    A_WORD12,
    A_WORD24,
    A_WORD15,
    A_WORD18,
    A_WORD21,
    A_WORD_MORE_LENGTHS,
    A_WORD_REVIEW,
    A_WORD_RESTART,
    A_CONFIRM_PASS,
    A_CONFIRM_NSEC,
    A_CHECK_BACKUP,
    A_CHECK_QR,
    A_RETRY_QUIZ,
    A_CONTINUE,
    A_PAUSE_QR,
    A_STEP_QR,
    A_KEY_QR,
    A_GROUP,
    A_START_GROUP,
    A_IMPORT_SHARE,
    A_SHARE_BACKUP,
    A_GROUP_RECORD,
    A_THRESHOLD_SENT,
    A_SHARE_QR,
    A_SHARE_SAVE,
    A_SHARE_SAVE_CONFIRM,
    A_SHARE_LOAD,
    A_SHARE_SCAN,
    A_GROUP_QR,
    A_IDENTITY_OPTIONS,
    A_ENTER_PASS,
    A_SCAN_PASS,
    A_REPAIR_SHARE,
    A_JOIN_REPAIR,
    A_RESPONSE_REASON
};
enum { INPUT_NSEC = 1, INPUT_PASS, INPUT_ACCOUNT };

static void show(void);
static void start_review(void);
static void finish_identity(void);
static void input_done(void);
static void threshold_next(void);
ns_context *device_core(void) { return core; }
static bool threshold_loaded(void) {
    return ns_is_loaded(core) && ns_threshold_state(core) != NS_THRESHOLD_NONE;
}
static void wipe_inputs(void) {
    platform_wipe(source, sizeof(source));
    platform_wipe(passphrase, sizeof(passphrase));
    platform_wipe(account_text, sizeof(account_text));
    source_len = passphrase_len = input_len = 0;
}
static void clear_presentation(void) {
    if (!platform_secret_clear())
        platform_fail();
    platform_wipe(secret_page, sizeof(secret_page));
    platform_wipe(qr_frame, sizeof(qr_frame));
    platform_wipe(share_backup, sizeof(share_backup));
    qr_length = 0;
    if (public_body) {
        platform_public_free(public_body);
        public_body = NULL;
    }
}
static void stop_scan(void) {
    if (scanning && !platform_scan_stop())
        platform_fail();
    scanning = false;
}
static void lock_identity(void) {
    platform_revoke();
    stop_scan();
    clear_presentation();
    ns_lock(core);
    wipe_inputs();
    platform_wipe(&word_draft, sizeof(word_draft));
    have_word_draft = false;
    platform_wipe(&quiz, sizeof(quiz));
    platform_wipe(backup_expected, sizeof(backup_expected));
    backup_expected_len = 0;
    backup_checked = false;
    has_passphrase = false;
    editing_account = false;
    threshold_restoring = false;
    threshold_packet = 0;
    response_error = 0;
    platform_wipe(public_key, sizeof(public_key));
    platform_wipe(npub, sizeof(npub));
    state = HOME;
    partial = false;
}
static void error_message(const char *text, unsigned next) {
    stop_scan();
    clear_presentation();
    ns_cancel(core);
    wipe_inputs();
    editing_account = false;
    snprintf(message, sizeof(message), "%s", text);
    notice_return = next;
    state = NOTICE;
    show();
}
static bool result_ok(int32_t result) {
    if (result == NS_OK)
        return true;
    error_message(ns_error_text(result), HOME);
    return false;
}
static void share_file_error(share_file_result result, unsigned next) {
    const char *text =
        result == SHARE_FILE_UNAVAILABLE
            ? "No readable SD card. Use a FAT-formatted card; the device never formats it."
        : result == SHARE_FILE_EXISTS
            ? "NSEALR.NSR already exists. No file was replaced. Use a different card."
        : result == SHARE_FILE_MISSING ? "No NSEALR.NSR file was found at the root of this card."
        : result == SHARE_FILE_INVALID
            ? "The share file is empty or too large. No identity was loaded."
            : "The card could not complete the transfer. The backup was not verified.";
    error_message(text, next);
}
static bool public_identity(void) {
    size_t n = 0;
    if (ns_public_key(core, 0, (uint8_t *)public_key, 64, &n) != NS_OK || n != 64)
        return false;
    public_key[n] = 0;
    if (ns_public_key(core, 1, (uint8_t *)npub, 64, &n) != NS_OK || n >= sizeof(npub))
        return false;
    npub[n] = 0;
    return true;
}
static void begin_identity(bool create) {
    lock_identity();
    platform_new_context();
    generating = create;
    words = 0;
    account = 0;
    source_kind = 0;
    backup_prompt = create;
    state = create ? CREATE : IMPORT;
    deadline = platform_now() + 600000;
    show();
}
static void entry(unsigned target) {
    input_target = target;
    input_len = 0;
    keyboard_page = target == INPUT_ACCOUNT ? 1 : 0;
    keyboard_upper = false;
    state = ENTRY;
    show();
}
static void recover(void) {
    int32_t status;
    bool applied_pass = passphrase_len > 0;
    uint32_t derive_account = editing_account ? requested_account : account;
    if (have_word_draft && !words_assemble(&word_draft, source, sizeof(source), &source_len))
        platform_fail();
    if (generating) {
        if (!platform_random32(entropy)) {
            error_message("Random source unavailable. No identity was created.", HOME);
            return;
        }
        status = ns_generate(core, words, entropy, passphrase, passphrase_len, derive_account);
    } else if (source_kind == 1)
        status = ns_import_nsec(core, source, source_len);
    else if (source_kind == 2)
        status = ns_import_mnemonic(core, source, source_len, passphrase, passphrase_len,
                                    derive_account);
    else
        status = ns_import_secret_qr(core, source_kind - 2, source, source_len, passphrase,
                                     passphrase_len, derive_account);
    wipe_inputs();
    if (!result_ok(status))
        return;
    platform_wipe(&word_draft, sizeof(word_draft));
    have_word_draft = false;
    if (!public_identity()) {
        lock_identity();
        error_message("Could not read the identity.", HOME);
        return;
    }
    has_passphrase = applied_pass;
    account = derive_account;
    editing_account = false;
    state = IDENTITY;
    show();
}
static void finish_identity(void) { recover(); }
static void input_done(void) {
    if (input_target == INPUT_ACCOUNT) {
        account_text[input_len] = 0;
        char *end = NULL;
        unsigned long n = strtoul(account_text, &end, 10);
        if (!input_len || *end || n > 0x7fffffffUL) {
            error_message("Use an account number from 0 to 2147483647.", IDENTITY);
            return;
        }
        requested_account = (uint32_t)n;
        if (has_passphrase) {
            state = PASSPHRASE_HELP;
            show();
            return;
        }
        recover();
        return;
    }
    if (input_target == INPUT_PASS) {
        passphrase_len = input_len;
        private_offset = 0;
        state = PASSPHRASE_REVIEW;
        show();
        return;
    }
    source_len = input_len;
    source_kind = 1;
    state = NSEC_REVIEW;
    show();
}
static void validate_words(void) {
    if (!words_assemble(&word_draft, source, sizeof(source), &source_len))
        platform_fail();
    int32_t result = ns_import_mnemonic(core, source, source_len, passphrase, 0, 0);
    ns_lock(core);
    source_len = 0;
    source_kind = 2;
    have_word_draft = true;
    state = result == NS_OK ? WORD_REVIEW : WORD_INVALID;
    show();
}
static void show_word_entry(void) {
    snprintf(message, sizeof(message), "Word %u of %u", word_draft.position + 1, word_draft.count);
    view.screen = UI_WORD_ENTRY;
    view.title = message;
    view.left_label = word_draft.position ? "Previous" : "Back";
    view.left_action = UI_WORD_PREVIOUS;
    unsigned remaining = word_draft.match_count - word_draft.match_page;
    view.word_choices = word_draft.prefix_len >= 2 ? (remaining > 2 ? 2 : remaining) : 0;
    if (word_draft.prefix_len >= 2 && word_draft.match_count > 2) {
        view.right_label = "More matches";
        view.right_action = UI_WORD_MORE;
    }
    if (!platform_present(&view))
        platform_fail();
    static const uint8_t hint[] = "Start typing";
    ns_text lines[3] = {{word_draft.prefix_len ? word_draft.prefix : hint,
                         word_draft.prefix_len ? word_draft.prefix_len : sizeof(hint) - 1}};
    uint16_t y[3] = {108, 146, 190};
    for (unsigned i = 0; i < view.word_choices; i++)
        if (ns_wordlist_word(word_draft.matches[word_draft.match_page + i], &lines[i + 1]) != NS_OK)
            platform_fail();
    if (!platform_word_entry(lines, y, view.word_choices + 1, words_valid_letters(&word_draft)))
        platform_fail();
}
static void show_word_review(void) {
    unsigned first = word_review_page * 4, remaining = word_draft.count - first;
    view.screen = UI_WORD_REVIEW;
    view.title = "Review words";
    view.subtitle = "Tap a word to change it.";
    view.word_choices = remaining > 4 ? 4 : remaining;
    view.right_label = remaining > 4 ? "Next words" : "Continue";
    view.right_action = UI_NEXT;
    if (!platform_present(&view))
        platform_fail();
    uint8_t rows[4][14] = {{0}};
    ns_text lines[4];
    uint16_t y[4] = {146, 202, 258, 314};
    for (unsigned i = 0; i < view.word_choices; i++) {
        ns_text word;
        if (ns_wordlist_word(word_draft.words[first + i], &word) != NS_OK)
            platform_fail();
        int n = snprintf((char *)rows[i], sizeof(rows[i]), "%02u %.*s", first + i + 1,
                         (int)word.len, word.data);
        if (n < 0 || n > 13)
            platform_fail();
        lines[i] = (ns_text){rows[i], (size_t)n};
    }
    bool ok = platform_secret_lines(lines, y, view.word_choices);
    platform_wipe(rows, sizeof(rows));
    if (!ok)
        platform_fail();
}
static void scan(unsigned target) {
    scan_target = target;
    state = SCAN;
    if (target != SCAN_REQUEST && target != SCAN_THRESHOLD)
        ns_cancel(core);
    deadline = platform_now() + 600000;
    show();
    if (!platform_scan_start()) {
        error_message("Camera could not start.",
                      target == SCAN_BACKUP_CHECK || target == SCAN_SHARE_CHECK ? BACKUP_OPTIONS
                      : target == SCAN_KEY || target == SCAN_SHARE_IMPORT       ? IMPORT
                      : target == SCAN_PASSPHRASE                               ? IDENTITY
                                                                                : HOME);
        return;
    }
    scanning = true;
}
static bool read_item(uint32_t index, ns_text *label, ns_text *value, uint32_t *flags) {
    return ns_review_item(core, index, label, value, flags) == NS_OK;
}
static void start_review(void) {
    review_generation = ns_review_generation(core);
    review_index = UINT32_MAX;
    partial = false;
    reading_details = false;
    private_offset = 0;
    reader_done = false;
    state = REVIEW;
    show();
}
static void next_review(void) {
    uint32_t count = ns_review_count(core);
    review_index = review_index == UINT32_MAX ? 0 : review_index + 1;
    while (review_index < count) {
        ns_text l, v;
        uint32_t f;
        if (!read_item(review_index, &l, &v, &f)) {
            error_message("Request changed.", HOME);
            return;
        }
        if (((f & NS_REVIEW_PROSE) && !(f & NS_REVIEW_CRITICAL)) ||
            ((f & NS_REVIEW_PRIVATE) && (f & NS_REVIEW_CRITICAL)))
            break;
        review_index++;
    }
    private_offset = 0;
    reader_done = false;
    state = review_index < count ? REVIEW : DECISION;
    show();
}
static bool format_private_page(ns_text value, size_t *written) {
    size_t out = 0, columns = 0;
    unsigned lines = 0;
    while (private_offset < value.len && lines < 6) {
        uint8_t first = value.data[private_offset];
        size_t bytes = first < 128 ? 1 : first < 224 ? 2 : first < 240 ? 3 : 4;
        char token[16] = {0};
        size_t token_len = 0;
        if (bytes > value.len - private_offset ||
            !ui_escape_text(value.data + private_offset, bytes, token, sizeof(token), &token_len))
            return false;
        if (state == PASSPHRASE_REVIEW && token_len == 1 && token[0] == ' ') {
            memcpy(token, "[space]", 7);
            token_len = 7;
        } else if (state == PASSPHRASE_REVIEW && token_len == 1 && token[0] == '[') {
            token[0] = '\\';
            token[1] = '[';
            token_len = 2;
        }
        if (token_len == 1 && token[0] == '\n') {
            token[0] = '\\';
            token[1] = 'n';
            token_len = 2;
        }
        if (columns + token_len > 16) {
            secret_page[out++] = '\n';
            columns = 0;
            if (++lines == 6) {
                platform_wipe(token, sizeof(token));
                break;
            }
        }
        memcpy(secret_page + out, token, token_len);
        out += token_len;
        columns += token_len;
        private_offset += bytes;
        platform_wipe(token, sizeof(token));
    }
    *written = out;
    return true;
}
static bool private_page(ns_text value) {
    size_t n = 0;
    return format_private_page(value, &n) && platform_secret_text(secret_page, n);
}
static bool authority_view(void) {
    size_t cap = 1, at = 0;
    uint32_t count = ns_review_count(core);
    for (uint32_t i = 0; i < count; i++) {
        ns_text l, v;
        uint32_t f;
        if (!read_item(i, &l, &v, &f))
            return false;
        if (!(f & NS_REVIEW_CRITICAL) || (f & NS_REVIEW_PRIVATE))
            continue;
        size_t extra = (l.len + v.len) * 10 + 3;
        if (extra > 327680 - cap)
            return false;
        cap += extra;
    }
    public_body = platform_public_alloc(cap);
    if (!public_body)
        return false;
    for (uint32_t i = 0; i < count; i++) {
        ns_text l, v;
        uint32_t f;
        size_t n;
        if (!read_item(i, &l, &v, &f))
            return false;
        if (!(f & NS_REVIEW_CRITICAL) || (f & NS_REVIEW_PRIVATE))
            continue;
        if (!ui_escape_text(l.data, l.len, public_body + at, cap - at, &n))
            return false;
        at += n;
        public_body[at++] = '\n';
        if (!ui_escape_text(v.data, v.len, public_body + at, cap - at, &n))
            return false;
        at += n;
        public_body[at++] = '\n';
        public_body[at++] = '\n';
    }
    public_body[at] = 0;
    review_flags = NS_REVIEW_CRITICAL;
    view.screen = UI_READER;
    view.title = "Review request";
    view.subtitle = "Action, identity and authority";
    view.body = public_body;
    view.left_label = "Reject";
    view.left_action = UI_CANCEL;
    view.right_label = "Next";
    view.right_action = UI_NEXT;
    view.right_enabled = reader_done;
    return true;
}
static bool review_view(void) {
    if (review_index == UINT32_MAX && !reading_details)
        return authority_view();
    ns_text label, value;
    if (!read_item(review_index, &label, &value, &review_flags))
        return false;
    size_t n = 0;
    if (!ui_escape_text(label.data, label.len, caption, sizeof(caption), &n))
        return false;
    view.title = reading_details ? "Exact details" : "Review request";
    view.subtitle = caption;
    view.left_label = reading_details ? "Back" : "Reject";
    view.left_action = reading_details ? A_RESUME_REVIEW : UI_CANCEL;
    view.right_label = "Next";
    view.right_action = UI_NEXT;
    view.right_enabled = reader_done;
    if (!reading_details && (review_flags & NS_REVIEW_PROSE) &&
        !(review_flags & NS_REVIEW_CRITICAL)) {
        view.aux_label = "Skip text";
        view.aux_action = A_SKIP_TEXT;
    }
    if (review_flags & NS_REVIEW_PRIVATE) {
        view.screen = UI_SECRET;
        view.right_enabled = true;
        view.right_label = private_offset ? "Next" : "Read";
    } else {
        size_t cap = value.len * 10 + 1;
        if (cap > 327681)
            return false;
        public_body = platform_public_alloc(cap);
        if (!public_body || !ui_escape_text(value.data, value.len, public_body, cap, &n))
            return false;
        view.screen = UI_READER;
        view.body = public_body;
    }
    return true;
}
static void response(void) {
    ns_text json;
    size_t share_len = 0;
    int32_t result;
    if (state == SHARE_QR) {
        result = ns_threshold_backup(core, share_backup, sizeof(share_backup), &share_len);
        json = (ns_text){share_backup, share_len};
    } else if (state == GROUP_QR) {
        public_body = platform_public_alloc(1024);
        if (!public_body)
            platform_fail();
        result = ns_threshold_record(core, (uint8_t *)public_body, 1024, &share_len);
        json = (ns_text){(const uint8_t *)public_body, share_len};
    } else if (state == THRESHOLD_QR)
        result = ns_threshold_output(core, threshold_packet, &json);
    else
        result = ns_response(core, &json);
    if (result != NS_OK) {
        error_message("No response is available.", HOME);
        return;
    }
    uint32_t frames = (uint32_t)((json.len + NS_QR_CHUNK - 1) / NS_QR_CHUNK);
    if (!frames)
        platform_fail();
    response_frame %= frames;
    if (ns_encode_frame(json.data, json.len, response_frame, qr_frame, sizeof(qr_frame),
                        &qr_length) != NS_OK) {
        error_message("The response is too large for QR.", HOME);
        return;
    }
    platform_wipe(share_backup, sizeof(share_backup));
    snprintf(caption, sizeof(caption), "Frame %u of %u", (unsigned)response_frame + 1,
             (unsigned)frames);
    view.screen = UI_SECRET;
    view.title = "Return to client";
    view.subtitle = caption;
    view.left_label = "Done";
    view.left_action = UI_DONE;
    if (state == THRESHOLD_QR) {
        uint32_t phase = ns_threshold_state(core);
        view.title =
            phase == NS_THRESHOLD_JOIN ? (threshold_restoring ? "Join repair" : "Join group")
            : phase == NS_THRESHOLD_READY && threshold_packet + 1 == ns_threshold_output_count(core)
                ? "Group record"
            : phase == NS_THRESHOLD_RESULT ? "Return to client"
                                           : "Share with client";
        snprintf(caption, sizeof(caption), "Packet %u of %u\nFrame %u of %u",
                 (unsigned)threshold_packet + 1, (unsigned)ns_threshold_output_count(core),
                 (unsigned)response_frame + 1, (unsigned)frames);
        view.left_label = "Captured";
        view.left_action = A_THRESHOLD_SENT;
    } else if (state == RESPONSE && response_error) {
        view.title = "Request refused";
        if (frames > 1) {
            view.header_label = "Reason";
            view.header_action = A_RESPONSE_REASON;
        } else {
            view.right_label = "Reason";
            view.right_action = A_RESPONSE_REASON;
        }
    } else if (state == SHARE_QR) {
        view.title = "Private share";
        snprintf(caption, sizeof(caption), "Save every frame.\nFrame %u of %u",
                 (unsigned)response_frame + 1, (unsigned)frames);
    } else if (state == GROUP_QR) {
        view.title = "Group record";
        view.left_label = "View text";
        view.left_action = A_GROUP_RECORD;
    }
    if (frames > 1) {
        view.right_label = response_paused ? "Resume" : "Pause";
        view.right_action = A_PAUSE_QR;
        view.aux_label = "Next";
        view.aux_action = A_STEP_QR;
    } else
        response_paused = true;
    if (!platform_present(&view) || !platform_secret_qr(qr_frame, qr_length))
        platform_fail();
    last_frame = platform_now();
}
static void threshold_next(void) {
    if (ns_threshold_state(core) == NS_THRESHOLD_REVIEW) {
        start_review();
        return;
    }
    if (ns_threshold_state(core) == NS_THRESHOLD_READY && !public_identity()) {
        lock_identity();
        error_message("Could not read the group identity.", HOME);
        return;
    }
    if (ns_threshold_output_count(core)) {
        threshold_packet = response_frame = 0;
        response_paused = false;
        state = THRESHOLD_QR;
        show();
    } else if (ns_threshold_state(core) == NS_THRESHOLD_READY) {
        state = GROUP_READY;
        show();
    } else
        scan(SCAN_THRESHOLD);
}
static void approve(bool partial_prose) {
    clear_presentation();
    if (!platform_random32(entropy)) {
        error_message("Random source unavailable. Request cancelled.", HOME);
        return;
    }
    if (!result_ok(ns_approve(core, review_generation, partial_prose, entropy, sizeof(entropy),
                              platform_now())))
        return;
    if (ns_threshold_state(core) != NS_THRESHOLD_NONE) {
        threshold_next();
        return;
    }
    state = RESPONSE;
    response_error = 0;
    response_frame = 0;
    response_paused = false;
    deadline = platform_now() + 120000;
    show();
}
static void show_backup(void) {
    size_t n = 0;
    clear_presentation();
    view = (ui_view){.screen = UI_SECRET,
                     .title = "Secret backup",
                     .subtitle = caption,
                     .loaded = true,
                     .left_label = "Back",
                     .left_action = UI_BACK,
                     .right_label = "Next",
                     .right_action = UI_NEXT,
                     .right_enabled = true};
    if (state == REVEAL_WORDS) {
        uint32_t count = ns_word_count(core);
        snprintf(caption, sizeof(caption), "Words %u-%u of %u", (unsigned)backup_page * 6 + 1,
                 (unsigned)(backup_page * 6 + 6 < count ? backup_page * 6 + 6 : count),
                 (unsigned)count);
        for (uint32_t i = backup_page * 6; i < count && i < backup_page * 6 + 6; i++) {
            uint8_t word[16];
            size_t wn = 0;
            if (ns_backup_word(core, i, word, sizeof(word), &wn) != NS_OK)
                platform_fail();
            int added = snprintf((char *)secret_page + n, sizeof(secret_page) - n, "%02u %.*s\n",
                                 (unsigned)i + 1, (int)wn, word);
            platform_wipe(word, sizeof(word));
            if (added < 0 || (size_t)added >= sizeof(secret_page) - n)
                platform_fail();
            n += (size_t)added;
        }
        if (n)
            secret_page[--n] = 0;
        view.right_label = (backup_page + 1) * 6 >= count ? "Done" : "Next";
        if (!platform_present(&view) || !platform_secret_text(secret_page, n))
            platform_fail();
    } else {
        if (ns_backup(core, backup_kind, source, sizeof(source), &n) != NS_OK)
            platform_fail();
        view.right_label = state == REVEAL_NSEC ? "Show QR" : "Done";
        if (state == REVEAL_NSEC)
            view.right_action = A_KEY_QR;
        view.title = backup_kind == 1 ? (ns_word_count(core) ? "Derived nsec" : "Private key")
                                      : "Recovery words QR";
        snprintf(caption, sizeof(caption), "%s",
                 backup_kind == 1 ? (ns_word_count(core) ? "Only this identity, not recovery words."
                                                         : "Keep this private key safe.")
                                  : "Passphrase and account are excluded.");
        if (!platform_present(&view))
            platform_fail();
        bool ok =
            state == REVEAL_QR ? platform_secret_qr(source, n) : platform_secret_text(source, n);
        platform_wipe(source, sizeof(source));
        if (!ok)
            platform_fail();
    }
}
static void show(void) {
    clear_presentation();
    view = (ui_view){.loaded = ns_is_loaded(core),
                     .right_enabled = true,
                     .left_label = "Back",
                     .left_action = UI_BACK};
    static const ui_choice home_locked[] = {{"Create identity", A_CREATE},
                                            {"Import identity", A_IMPORT}};
    static const ui_choice home_ready[] = {{"Scan a request", A_SCAN},
                                           {"Public identity", A_PUBLIC},
                                           {"Back up identity", A_BACKUP},
                                           {"Clear identity", UI_LOCK}};
    static const ui_choice home_words[] = {{"Scan a request", A_SCAN},
                                           {"Public identity", A_PUBLIC},
                                           {"Back up identity", A_BACKUP},
                                           {"Identity options", A_IDENTITY_OPTIONS},
                                           {"Clear identity", UI_LOCK}};
    static const ui_choice create[] = {{"12 recovery words", A_GEN12},
                                       {"24 recovery words", A_GEN24},
                                       {"Standalone private key", A_GEN_RAW},
                                       {"2-of-3 signing group", A_GROUP}};
    static const ui_choice imports[] = {{"Scan a backup", A_SECRET_QR},
                                        {"Enter recovery words", A_WORDS},
                                        {"Enter private key", A_NSEC},
                                        {"Restore a group share", A_IMPORT_SHARE}};
    static const ui_choice backups[] = {{"Recovery words", A_BACKUP_WORDS},
                                        {"SeedQR", A_BACKUP_SEEDQR},
                                        {"Compact SeedQR", A_BACKUP_COMPACT},
                                        {"Account private key", A_BACKUP_NSEC}};
    static const ui_choice raw_backup[] = {{"Private key text", A_BACKUP_NSEC},
                                           {"Private key QR", A_BACKUP_SEEDQR}};
    switch (state) {
    case HOME:
        view.screen = UI_HOME;
        view.title = "Your identity";
        if (view.loaded) {
            snprintf(caption, sizeof(caption), "%.13s...%.8s\n%s%s", npub, npub + strlen(npub) - 8,
                     threshold_loaded()    ? "2-of-3 group share"
                     : ns_word_count(core) ? "Recovery words"
                                           : "Standalone nsec",
                     backup_checked ? " - checked" : "");
            view.subtitle = caption;
        } else
            view.subtitle = "Create or recover your Nostr key.";
        view.choices = ns_word_count(core) ? home_words : view.loaded ? home_ready : home_locked;
        view.choice_count = ns_word_count(core) ? 5 : view.loaded ? 4 : 2;
        view.left_label = NULL;
        break;
    case CREATE:
        view.screen = UI_MENU;
        view.title = "Create identity";
        view.subtitle = "Your backup restores your identity.";
        view.choices = create;
        view.choice_count = 4;
        break;
    case IMPORT:
        view.screen = UI_MENU;
        view.title = "Import identity";
        view.subtitle = "Enter secrets only on this device.";
        view.choices = imports;
        view.choice_count = 4;
        break;
    case GROUP_INTRO:
        view.screen = UI_NOTICE;
        view.title = "2-of-3 group";
        view.body = "Three devices. Any two shares can sign for one Nostr identity.\n\n"
                    "Use the companion to connect them. Private messages are not supported.";
        view.right_label = "Start group";
        view.right_action = A_START_GROUP;
        break;
    case REPAIR_INTRO:
        view.screen = UI_NOTICE;
        view.title = "Repair lost share";
        view.body = "Use both remaining devices to restore the missing share. The npub stays "
                    "the same.\n\nOld copies remain valid. Keep old backups until all three "
                    "updated group records agree.";
        view.right_label = "Join repair";
        view.right_action = A_JOIN_REPAIR;
        break;
    case RESPONSE_REASON:
        view.screen = UI_READER;
        view.title = "Request refused";
        view.body = ns_error_text(response_error);
        view.right_label = "Done";
        view.right_action = UI_DONE;
        break;
    case GROUP_READY: {
        static const ui_choice ready[] = {{"Back up this share", A_BACKUP},
                                          {"View group record", A_GROUP_RECORD},
                                          {"Use identity", A_CONTINUE}};
        view.screen = UI_MENU;
        view.title = threshold_restoring ? "Share restored" : "Group ready";
        view.subtitle = "Save your share and group record.";
        view.choices = ready;
        view.choice_count = 3;
        break;
    }
    case GROUP_RECORD: {
        uint8_t group[64];
        uint32_t member;
        if (ns_threshold_info(core, group, &member) != NS_OK) {
            error_message("Group record is unavailable.", HOME);
            return;
        }
        public_body = platform_public_alloc(384);
        if (!public_body)
            platform_fail();
        snprintf(public_body, 384,
                 "Member %u of 3. Any two shares can sign.\n\nGroup fingerprint\n%.*s\n\n"
                 "Nostr identity\n%s\n\nKeep this public record separately from your share "
                 "backup. Compare it when restoring.",
                 (unsigned)member, 64, group, npub);
        view.screen = UI_READER;
        view.title = "Group record";
        view.body = public_body;
        view.right_label = "Show QR";
        view.right_action = A_GROUP_QR;
        break;
    }
    case SHARE_BACKUP: {
        static const ui_choice methods[] = {{"Save to SD card", A_SHARE_SAVE_CONFIRM},
                                            {"Show offline QR", A_SHARE_BACKUP}};
        view.screen = UI_MENU;
        view.title = "Back up share";
        view.subtitle = "Keep this secret share offline.";
        view.choices = methods;
        view.choice_count = 2;
        break;
    }
    case SHARE_RESTORE: {
        static const ui_choice methods[] = {{"Scan share QR", A_SHARE_SCAN},
                                            {"Read from SD card", A_SHARE_LOAD},
                                            {"Repair lost share", A_REPAIR_SHARE}};
        view.screen = UI_MENU;
        view.title = "Restore share";
        view.subtitle = "Use a backup or both remaining devices.";
        view.choices = methods;
        view.choice_count = 3;
        break;
    }
    case SHARE_SAVE_CONSENT:
        view.screen = UI_NOTICE;
        view.title = "Save private share";
        view.body = "Write the unencrypted NSEALR.NSR file to this SD card. Keep the card offline "
                    "and separate from other shares.\n\nExisting files are never replaced.";
        view.right_label = "Save share";
        view.right_action = A_SHARE_SAVE;
        break;
    case SHARE_SAVED:
        view.screen = UI_NOTICE;
        view.title = "Share saved";
        view.body = "NSEALR.NSR was saved and read back successfully. Keep this SD card offline "
                    "and separate from other shares.\n\nKeep the public group record elsewhere.";
        view.right_label = "Continue";
        view.right_action = A_CONTINUE;
        break;
    case SHARE_QR_CONSENT:
        view.screen = UI_NOTICE;
        view.title = "Back up share";
        view.body = "Capture every QR frame on an offline device. Never use the connected "
                    "companion.\n\nKeep shares separate. Any two can sign.";
        view.right_label = "Show share";
        view.right_action = A_SHARE_QR;
        break;
    case WORD_COUNT: {
        static const ui_choice lengths[] = {{"12 words", A_WORD12},
                                            {"24 words", A_WORD24},
                                            {"Other word counts", A_WORD_MORE_LENGTHS}};
        view.screen = UI_MENU;
        view.title = "Recovery words";
        view.subtitle = "How many words are in your backup?";
        view.choices = lengths;
        view.choice_count = 3;
        break;
    }
    case WORD_MORE_LENGTHS: {
        static const ui_choice lengths[] = {
            {"15 words", A_WORD15}, {"18 words", A_WORD18}, {"21 words", A_WORD21}};
        view.screen = UI_MENU;
        view.title = "Word count";
        view.choices = lengths;
        view.choice_count = 3;
        break;
    }
    case WORD_ENTRY:
        show_word_entry();
        return;
    case WORD_REVIEW:
        show_word_review();
        return;
    case WORD_INVALID: {
        static const ui_choice repair[] = {{"Review and edit", A_WORD_REVIEW},
                                           {"Start again", A_WORD_RESTART}};
        view.screen = UI_MENU;
        view.title = "Check your words";
        view.subtitle = "Checksum did not match. Your words are kept.";
        view.choices = repair;
        view.choice_count = 2;
        break;
    }
    case ENTRY:
        view.screen = UI_INPUT;
        view.title = input_target == INPUT_NSEC   ? "Enter nsec"
                     : input_target == INPUT_PASS ? "Passphrase"
                                                  : "Account number";
        if (input_target == INPUT_ACCOUNT)
            view.body = account_text;
        view.input_length = input_len;
        view.keyboard_page = keyboard_page;
        view.keyboard_upper = keyboard_upper;
        view.left_label = "Cancel";
        view.left_action = UI_CANCEL;
        view.right_label = "Continue";
        view.right_action = UI_DONE;
        break;
    case IDENTITY: {
        static const ui_choice mnemonic[] = {{"Use identity", A_USE},
                                             {"Public npub", A_PUBLIC},
                                             {"Add / change passphrase", A_ADD_PASS},
                                             {"Advanced account", A_ACCOUNT_EDIT}};
        static const ui_choice raw[] = {{"Use identity", A_USE}, {"Public npub", A_PUBLIC}};
        snprintf(caption, sizeof(caption),
                 ns_word_count(core) ? "%u words - account %lu%s" : "Standalone nsec",
                 (unsigned)ns_word_count(core), (unsigned long)account,
                 has_passphrase ? "\nPassphrase applied" : "");
        view.screen = UI_MENU;
        view.title = "Identity ready";
        view.subtitle = caption;
        view.choices = ns_word_count(core) ? mnemonic : raw;
        view.choice_count = ns_word_count(core) ? 4 : 2;
        break;
    }
    case PUBLIC_TEXT:
        view.screen = UI_READER;
        view.title = "Your public npub";
        view.body = npub;
        view.right_label = "Show QR";
        view.right_action = A_PUBLIC;
        break;
    case NSEC_REVIEW:
        view.screen = UI_SECRET;
        view.title = "Check private key";
        view.subtitle = "Keep this screen private.";
        view.left_label = "Edit";
        view.right_label = "Import key";
        view.right_action = A_CONFIRM_NSEC;
        break;
    case PASSPHRASE_REVIEW:
        view.screen = UI_SECRET;
        view.title = "Check passphrase";
        {
            size_t first = private_offset;
            if (!format_private_page((ns_text){passphrase, passphrase_len}, &secret_page_len))
                platform_fail();
            snprintf(caption, sizeof(caption), "Bytes %zu-%zu of %zu\n[space] means a space.",
                     passphrase_len ? first + 1 : 0, private_offset, passphrase_len);
        }
        view.subtitle = caption;
        view.left_label = "Edit";
        view.right_label = private_offset < passphrase_len ? "Next page" : "Use passphrase";
        view.right_action = A_CONFIRM_PASS;
        break;
    case PASSPHRASE_HELP: {
        static const ui_choice methods[] = {{"Type passphrase", A_ENTER_PASS},
                                            {"Scan passphrase", A_SCAN_PASS}};
        view.screen = UI_MENU;
        view.title = "Passphrase";
        view.subtitle = editing_account ? "Use your existing passphrase."
                                        : "Changes your npub. Back up separately.";
        view.choices = methods;
        view.choice_count = 2;
        break;
    }
    case QUIZ: {
        snprintf(message, sizeof(message), "Choose word %u",
                 (unsigned)quiz.order[quiz.position] + 1);
        snprintf(caption, sizeof(caption), "Backup check %u of %u", quiz.position + 1, quiz.count);
        view.screen = UI_WORD_REVIEW;
        view.title = message;
        view.subtitle = caption;
        view.word_choices = 4;
        view.quiz = true;
        break;
    }
    case QUIZ_WRONG: {
        static const ui_choice retry[] = {{"Try this word again", A_RETRY_QUIZ},
                                          {"Review recovery words", A_BACKUP_WORDS},
                                          {"Continue without checking", A_CONTINUE}};
        view.screen = UI_MENU;
        view.title = "Check that word";
        view.subtitle = "That choice did not match your backup.";
        view.choices = retry;
        view.choice_count = 3;
        break;
    }
    case BACKUP_GOOD:
        view.screen = UI_NOTICE;
        view.title = "Backup checked";
        view.body = threshold_loaded()
                        ? "This backup matches this device's group share. Keep shares in separate "
                          "safe places, and keep the public group record separately."
                    : backup_kind == 1
                        ? "This backup matches your Nostr private key. Keep it private."
                        : "Recovery words match. Save your passphrase and account separately; they "
                          "are not in this backup.";
        view.right_label = "Continue";
        view.right_action = A_CONTINUE;
        break;
    case BACKUP_BAD:
        view.screen = UI_NOTICE;
        view.title = "Different backup";
        view.body =
            "This QR does not match the backup shown. Your loaded identity has not changed.";
        view.right_label = "Try again";
        view.right_action = A_CHECK_QR;
        break;
    case PUBLIC_IDENTITY:
        view.screen = UI_QR;
        view.title = "Public identity";
        view.subtitle = "Share this npub with your client.";
        view.qr = (const uint8_t *)npub;
        view.qr_length = strlen(npub);
        view.right_label = "View text";
        view.right_action = A_PUBLIC_TEXT;
        if (threshold_loaded()) {
            view.aux_label = "Record";
            view.aux_action = A_GROUP_RECORD;
        }
        break;
    case SCAN:
        view.screen = UI_SCAN;
        view.title =
            scan_target == SCAN_PASSPHRASE                                ? "Scan passphrase"
            : scan_target == SCAN_SHARE_IMPORT                            ? "Restore share"
            : scan_target == SCAN_SHARE_CHECK                             ? "Check share"
            : scan_target == SCAN_KEY || scan_target == SCAN_BACKUP_CHECK ? "Scan your backup"
            : scan_target == SCAN_THRESHOLD && ns_threshold_state(core) == NS_THRESHOLD_JOIN
                ? "Scan group setup"
            : scan_target == SCAN_THRESHOLD && ns_threshold_state(core) == NS_THRESHOLD_EXCHANGE
                ? "Scan next packet"
                : "Scan a request";
        view.subtitle = "Keep the QR inside the camera view.";
        if (scan_target == SCAN_PASSPHRASE)
            view.subtitle = "Offline text QR. Up to 256 UTF8 bytes.";
        if (scan_target == SCAN_THRESHOLD && ns_threshold_state(core) == NS_THRESHOLD_EXCHANGE) {
            snprintf(caption, sizeof(caption), "Peer packets received: %u of %u",
                     (unsigned)ns_threshold_progress(core), ns_is_loaded(core) ? 1u : 2u);
            view.subtitle = caption;
        }
        view.progress = ns_frames_received(core);
        view.total = ns_frames_expected(core);
        view.left_label = "Cancel";
        view.left_action = UI_CANCEL;
        break;
    case REVIEW:
    case DETAILS:
        if (!review_view()) {
            error_message("Cannot display this request safely.", HOME);
            return;
        }
        break;
    case DECISION:
        view.screen = UI_MENU;
        view.title = "Your decision";
        view.subtitle = "Only this request will be approved.";
        ns_text label;
        size_t length;
        if (ns_review_confirmation(core, &label) != NS_OK ||
            !ui_escape_text(label.data, label.len, confirmation, sizeof(confirmation), &length)) {
            error_message("Request is no longer available.", HOME);
            return;
        }
        static ui_choice decide[] = {
            {NULL, A_APPROVE}, {"View exact details", A_DETAILS}, {"Reject request", UI_CANCEL}};
        decide[0].label = confirmation;
        view.choices = decide;
        view.choice_count = 3;
        break;
    case PARTIAL:
        view.screen = UI_CONFIRM;
        view.title = "Partial review";
        view.body = "You did not view all the text. Unseen text may change the meaning of this "
                    "request. This approval applies only to this request.";
        view.right_label = "Approve anyway";
        view.right_action = A_PARTIAL_APPROVE;
        break;
    case RESPONSE:
    case THRESHOLD_QR:
    case SHARE_QR:
    case GROUP_QR:
        if (state == THRESHOLD_QR)
            view.loaded = true;
        response();
        return;
    case BACKUP:
        view.screen = UI_MENU;
        view.title = "Back up identity";
        view.subtitle = "Anyone with the backup can use your key.";
        view.choices = ns_word_count(core) ? backups : raw_backup;
        view.choice_count = ns_word_count(core) ? 4 : 2;
        break;
    case REVEAL_WORDS:
    case REVEAL_NSEC:
    case REVEAL_QR:
        show_backup();
        return;
    case BACKUP_OPTIONS: {
        static const ui_choice check_words[] = {{"Check my backup", A_CHECK_BACKUP},
                                                {"Continue", A_CONTINUE}};
        static const ui_choice check_qr[] = {{"Scan to check", A_CHECK_QR},
                                             {"Continue", A_CONTINUE}};
        view.screen = UI_MENU;
        view.title = "Backup saved?";
        view.subtitle = threshold_loaded()    ? "A share backup contains all QR frames."
                        : ns_word_count(core) ? "Seed backups exclude passphrase and account."
                                              : "Your nsec restores this identity.";
        view.choices = !threshold_loaded() && backup_kind == 2 ? check_words : check_qr;
        view.choice_count = 2;
        break;
    }
    case NOTICE:
        view.screen = UI_NOTICE;
        view.title = "Please check";
        view.body = message;
        view.right_label = "Continue";
        view.right_action = UI_DONE;
        view.left_label = NULL;
        break;
    }
    if (!platform_present(&view))
        platform_fail();
    if (state == NSEC_REVIEW) {
        if (!platform_secret_text(source, source_len))
            platform_fail();
        return;
    }
    if (state == PASSPHRASE_REVIEW) {
        if (!platform_secret_text(secret_page, secret_page_len))
            platform_fail();
        return;
    }
    if (state == QUIZ) {
        ns_text lines[4];
        uint16_t y[4] = {146, 202, 258, 314};
        for (unsigned i = 0; i < 4; i++)
            if (ns_wordlist_word(quiz.choices[i], &lines[i]) != NS_OK)
                platform_fail();
        if (!platform_secret_lines(lines, y, 4))
            platform_fail();
        return;
    }
    if ((state == REVIEW || state == DETAILS) && (review_flags & NS_REVIEW_PRIVATE)) {
        ns_text l, v;
        uint32_t f;
        if (!read_item(review_index, &l, &v, &f) || !private_page(v))
            platform_fail();
        reader_done = private_offset >= v.len;
        if (reader_done && !reading_details &&
            ns_review_seen(core, review_generation, review_index) != NS_OK)
            platform_fail();
    }
}
void device_presented(bool at_end) {
    if (state != REVIEW && state != DETAILS)
        return;
    if (!(review_flags & NS_REVIEW_PRIVATE) && at_end) {
        reader_done = true;
        if (!reading_details) {
            if (review_index == UINT32_MAX) {
                for (uint32_t i = 0; i < ns_review_count(core); i++) {
                    ns_text l, v;
                    uint32_t f;
                    if (!read_item(i, &l, &v, &f))
                        platform_fail();
                    if ((f & NS_REVIEW_CRITICAL) && !(f & NS_REVIEW_PRIVATE) &&
                        ns_review_seen(core, review_generation, i) != NS_OK)
                        platform_fail();
                }
            } else if (ns_review_seen(core, review_generation, review_index) != NS_OK)
                platform_fail();
        }
        platform_review_ready();
    }
}
void device_action(unsigned action) {
    if (action == UI_LOCK) {
        lock_identity();
        backup_prompt = false;
        show();
        return;
    }
    if (action == UI_READER_END) {
        device_presented(true);
        return;
    }
    if (state == QUIZ && action >= UI_WORD_EDIT0 && action <= UI_WORD_EDIT3) {
        if (!backup_check_answer(&quiz, action - UI_WORD_EDIT0))
            state = QUIZ_WRONG;
        else if (quiz.position == quiz.count) {
            backup_checked = true;
            platform_wipe(&quiz, sizeof(quiz));
            state = BACKUP_GOOD;
        }
        show();
        return;
    }
    if (state == WORD_ENTRY) {
        if (action >= 'a' && action <= 'z') {
            words_type(&word_draft, action);
            show();
            return;
        }
        if (action == UI_KEY_BACKSPACE) {
            words_erase(&word_draft);
            show();
            return;
        }
        if (action == UI_KEY_CLEAR) {
            while (word_draft.prefix_len)
                words_erase(&word_draft);
            show();
            return;
        }
        if (action == UI_WORD_MORE) {
            word_draft.match_page += 2;
            if (word_draft.match_page >= word_draft.match_count)
                word_draft.match_page = 0;
            show();
            return;
        }
        if (action == UI_WORD_PREVIOUS) {
            if (word_draft.position)
                words_edit(&word_draft, word_draft.position - 1);
            else
                state = WORD_COUNT;
            show();
            return;
        }
        if (action == UI_WORD_FIRST || action == UI_WORD_SECOND) {
            if (!words_choose(&word_draft, action == UI_WORD_SECOND ? 1 : 0))
                return;
            if (editing_word || word_draft.position + 1 == word_draft.count) {
                editing_word = false;
                validate_words();
            } else {
                words_edit(&word_draft, word_draft.position + 1);
                show();
            }
            return;
        }
    }
    if (state == WORD_REVIEW && action >= UI_WORD_EDIT0 && action <= UI_WORD_EDIT3) {
        unsigned position = word_review_page * 4 + action - UI_WORD_EDIT0;
        if (position >= word_draft.count)
            return;
        words_edit(&word_draft, position);
        editing_word = true;
        state = WORD_ENTRY;
        show();
        return;
    }
    if (state == ENTRY) {
        uint8_t *buf = input_target == INPUT_PASS      ? passphrase
                       : input_target == INPUT_ACCOUNT ? (uint8_t *)account_text
                                                       : source;
        size_t cap = input_target == INPUT_PASS      ? sizeof(passphrase)
                     : input_target == INPUT_ACCOUNT ? sizeof(account_text) - 1
                                                     : 63;
        if (action >= 32 && action < 127) {
            if (input_len < cap)
                buf[input_len++] = (uint8_t)action;
            if (input_target == INPUT_ACCOUNT)
                show();
            else
                platform_input_changed(input_len);
            return;
        }
        if (action == UI_KEY_SPACE) {
            if (input_len < cap)
                buf[input_len++] = ' ';
            if (input_target == INPUT_ACCOUNT)
                show();
            else
                platform_input_changed(input_len);
            return;
        }
        if (action == UI_KEY_BACKSPACE) {
            if (input_len) {
                size_t start = input_len - 1;
                if (input_target == INPUT_PASS)
                    while (start && (buf[start] & 0xc0) == 0x80)
                        start--;
                platform_wipe(buf + start, input_len - start);
                input_len = start;
            }
            if (input_target == INPUT_ACCOUNT)
                show();
            else
                platform_input_changed(input_len);
            return;
        }
        if (action == UI_KEY_MODE) {
            keyboard_page = (keyboard_page + 1) % 3;
            show();
            return;
        }
        if (action == UI_KEY_CASE) {
            keyboard_upper = !keyboard_upper;
            show();
            return;
        }
        if (action == UI_DONE) {
            input_done();
            return;
        }
    }
    if (action == UI_CANCEL) {
        bool cancelled_passphrase = state == SCAN && scan_target == SCAN_PASSPHRASE;
        stop_scan();
        clear_presentation();
        wipe_inputs();
        editing_account = false;
        if (state == REVIEW || state == DETAILS || state == DECISION || state == PARTIAL) {
            bool threshold = ns_threshold_state(core) != NS_THRESHOLD_NONE;
            if (ns_reject(core, review_generation) == NS_OK) {
                state = threshold ? HOME : RESPONSE;
                response_error = 0;
                response_paused = false;
                response_frame = 0;
                deadline = platform_now() + 120000;
                show();
                return;
            }
        }
        ns_cancel(core);
        platform_wipe(&word_draft, sizeof(word_draft));
        have_word_draft = false;
        platform_wipe(&quiz, sizeof(quiz));
        platform_wipe(backup_expected, sizeof(backup_expected));
        backup_expected_len = 0;
        state = cancelled_passphrase ? IDENTITY : HOME;
        show();
        return;
    }
    if (action == UI_BACK) {
        if (state == REPAIR_INTRO || state == GROUP_INTRO || state == RESPONSE_REASON) {
            state = state == REPAIR_INTRO  ? SHARE_RESTORE
                    : state == GROUP_INTRO ? CREATE
                                           : RESPONSE;
            show();
            return;
        }
        if (state == PUBLIC_IDENTITY || state == PUBLIC_TEXT) {
            state = state == PUBLIC_TEXT ? PUBLIC_IDENTITY : public_return;
            show();
            return;
        }
        if (state == GROUP_RECORD) {
            state = record_return;
            show();
            return;
        }
        if (state == PASSPHRASE_HELP) {
            wipe_inputs();
            editing_account = false;
            state = IDENTITY;
            show();
            return;
        }
        if (state == NSEC_REVIEW) {
            input_target = INPUT_NSEC;
            input_len = source_len;
            state = ENTRY;
            show();
            return;
        }
        if (state == PASSPHRASE_REVIEW) {
            input_target = INPUT_PASS;
            input_len = passphrase_len;
            state = ENTRY;
            show();
            return;
        }
        if (state == QUIZ || state == QUIZ_WRONG) {
            platform_wipe(&quiz, sizeof(quiz));
            state = BACKUP;
            show();
            return;
        }
        if (state == WORD_REVIEW) {
            if (word_review_page)
                word_review_page--;
            else {
                words_edit(&word_draft, 0);
                editing_word = true;
                state = WORD_ENTRY;
            }
            show();
            return;
        }
        if (state == WORD_MORE_LENGTHS) {
            state = WORD_COUNT;
            show();
            return;
        }
        if (state == WORD_COUNT) {
            platform_wipe(&word_draft, sizeof(word_draft));
            have_word_draft = false;
            state = IMPORT;
            show();
            return;
        }
        if (state == REVEAL_WORDS && backup_page) {
            backup_page--;
            show();
            return;
        }
        if (state == PARTIAL) {
            state = DECISION;
            show();
            return;
        }
        if (state == REVIEW || state == DETAILS) {
            state = DECISION;
            show();
            return;
        }
        ns_cancel(core);
        platform_wipe(&word_draft, sizeof(word_draft));
        have_word_draft = false;
        platform_wipe(&quiz, sizeof(quiz));
        platform_wipe(backup_expected, sizeof(backup_expected));
        backup_expected_len = 0;
        state = ns_is_loaded(core) ? HOME : IMPORT;
        wipe_inputs();
        editing_account = false;
        show();
        return;
    }
    switch (action) {
    case A_GROUP:
        state = GROUP_INTRO;
        show();
        return;
    case A_REPAIR_SHARE:
        if (state != SHARE_RESTORE)
            return;
        state = REPAIR_INTRO;
        show();
        return;
    case A_START_GROUP:
    case A_JOIN_REPAIR:
        if ((action == A_START_GROUP && state != GROUP_INTRO) ||
            (action == A_JOIN_REPAIR && state != REPAIR_INTRO))
            return;
        lock_identity();
        threshold_restoring = action == A_JOIN_REPAIR;
        platform_new_context();
        if (!platform_random32(entropy)) {
            error_message("Random source unavailable. No group was created.", HOME);
            return;
        }
        if (result_ok(ns_threshold_start(core, entropy, platform_now()))) {
            deadline = platform_now() + 600000;
            threshold_next();
        }
        return;
    case A_IMPORT_SHARE:
        threshold_restoring = true;
        state = SHARE_RESTORE;
        show();
        return;
    case A_SHARE_SCAN:
        if (state != SHARE_RESTORE)
            return;
        scan(SCAN_SHARE_IMPORT);
        return;
    case A_SHARE_BACKUP:
        if (state != SHARE_BACKUP || !threshold_loaded())
            return;
        state = SHARE_QR_CONSENT;
        show();
        return;
    case A_SHARE_QR:
        if (state != SHARE_QR_CONSENT || !threshold_loaded())
            return;
        response_frame = 0;
        response_paused = false;
        state = SHARE_QR;
        show();
        return;
    case A_SHARE_SAVE_CONFIRM:
        if (state != SHARE_BACKUP || !threshold_loaded())
            return;
        state = SHARE_SAVE_CONSENT;
        show();
        return;
    case A_SHARE_SAVE: {
        if (state != SHARE_SAVE_CONSENT || !threshold_loaded())
            return;
        size_t length = 0;
        if (!result_ok(ns_threshold_backup(core, share_backup, sizeof(share_backup), &length)))
            return;
        share_file_result result = platform_share_save(share_backup, length);
        platform_wipe(share_backup, sizeof(share_backup));
        if (result != SHARE_FILE_OK)
            share_file_error(result, SHARE_BACKUP);
        else {
            backup_checked = true;
            state = SHARE_SAVED;
            show();
        }
        return;
    }
    case A_SHARE_LOAD: {
        if (state != SHARE_RESTORE)
            return;
        size_t length = 0;
        share_file_result result = platform_share_load(share_backup, sizeof(share_backup), &length);
        if (result != SHARE_FILE_OK) {
            platform_wipe(share_backup, sizeof(share_backup));
            share_file_error(result, SHARE_RESTORE);
            return;
        }
        int32_t status = ns_threshold_import(core, share_backup, length, platform_now());
        platform_wipe(share_backup, sizeof(share_backup));
        if (result_ok(status))
            start_review();
        return;
    }
    case A_GROUP_RECORD:
        if (!threshold_loaded())
            return;
        if (state != GROUP_QR)
            record_return = state;
        state = GROUP_RECORD;
        show();
        return;
    case A_GROUP_QR:
        if (state != GROUP_RECORD || !threshold_loaded())
            return;
        response_frame = 0;
        response_paused = false;
        state = GROUP_QR;
        show();
        return;
    case A_THRESHOLD_SENT:
        if (state != THRESHOLD_QR)
            return;
        if (++threshold_packet < ns_threshold_output_count(core)) {
            response_frame = 0;
            response_paused = false;
            show();
            return;
        }
        ns_finish_response(core);
        if (ns_threshold_state(core) == NS_THRESHOLD_RESULT) {
            state = HOME;
            show();
        } else
            threshold_next();
        return;
    case A_CREATE:
        begin_identity(true);
        return;
    case A_IMPORT:
        begin_identity(false);
        return;
    case A_GEN12:
    case A_GEN24:
    case A_GEN_RAW:
        words = action == A_GEN12 ? 12 : action == A_GEN24 ? 24 : 0;
        source_kind = words ? 2 : 1;
        recover();
        return;
    case A_WORDS:
        state = WORD_COUNT;
        show();
        return;
    case A_WORD12:
    case A_WORD24:
    case A_WORD15:
    case A_WORD18:
    case A_WORD21:
        words_begin(&word_draft, action == A_WORD12   ? 12
                                 : action == A_WORD24 ? 24
                                 : action == A_WORD15 ? 15
                                 : action == A_WORD18 ? 18
                                                      : 21);
        have_word_draft = true;
        word_review_page = 0;
        editing_word = false;
        state = WORD_ENTRY;
        show();
        return;
    case A_WORD_MORE_LENGTHS:
        state = WORD_MORE_LENGTHS;
        show();
        return;
    case A_WORD_REVIEW:
        word_review_page = 0;
        state = WORD_REVIEW;
        show();
        return;
    case A_WORD_RESTART:
        platform_wipe(&word_draft, sizeof(word_draft));
        have_word_draft = false;
        state = WORD_COUNT;
        show();
        return;
    case A_NSEC:
        memcpy(source, "nsec1", 5);
        source_len = 5;
        entry(INPUT_NSEC);
        input_len = 5;
        show();
        return;
    case A_CONFIRM_NSEC:
        if (state == NSEC_REVIEW)
            recover();
        return;
    case A_SECRET_QR:
        scan(SCAN_KEY);
        return;
    case A_ADD_PASS:
        if (ns_word_count(core)) {
            if (ns_backup(core, 2, source, sizeof(source), &source_len) != NS_OK)
                platform_fail();
            generating = false;
            source_kind = 2;
        }
        editing_account = false;
        state = PASSPHRASE_HELP;
        show();
        return;
    case A_ENTER_PASS:
        if (state != PASSPHRASE_HELP)
            return;
        entry(INPUT_PASS);
        return;
    case A_SCAN_PASS:
        if (state != PASSPHRASE_HELP)
            return;
        scan(SCAN_PASSPHRASE);
        return;
    case A_CONFIRM_PASS:
        if (state != PASSPHRASE_REVIEW)
            return;
        if (private_offset < passphrase_len) {
            show();
            return;
        }
        recover();
        return;
    case A_ACCOUNT_EDIT:
        if (ns_word_count(core)) {
            if (ns_backup(core, 2, source, sizeof(source), &source_len) != NS_OK)
                platform_fail();
            generating = false;
            source_kind = 2;
        }
        requested_account = account;
        editing_account = true;
        entry(INPUT_ACCOUNT);
        return;
    case A_IDENTITY_OPTIONS:
        if (!ns_word_count(core))
            return;
        backup_prompt = false;
        state = IDENTITY;
        show();
        return;
    case A_USE:
        if (backup_prompt && ns_word_count(core)) {
            backup_kind = 2;
            backup_page = 0;
            state = REVEAL_WORDS;
        } else if (backup_prompt)
            state = BACKUP;
        else
            state = HOME;
        show();
        return;
    case A_CONTINUE:
        platform_wipe(&quiz, sizeof(quiz));
        platform_wipe(backup_expected, sizeof(backup_expected));
        backup_expected_len = 0;
        backup_prompt = false;
        state = HOME;
        show();
        return;
    case A_CHECK_BACKUP:
        if (!platform_random32(entropy) || !backup_check_begin(&quiz, core, entropy))
            platform_fail();
        platform_wipe(entropy, sizeof(entropy));
        state = QUIZ;
        show();
        return;
    case A_RETRY_QUIZ:
        backup_check_question(&quiz);
        state = QUIZ;
        show();
        return;
    case A_CHECK_QR:
        if (threshold_loaded()) {
            scan(SCAN_SHARE_CHECK);
            return;
        }
        if (ns_backup(core, backup_kind, backup_expected, sizeof(backup_expected),
                      &backup_expected_len) != NS_OK)
            platform_fail();
        scan(SCAN_BACKUP_CHECK);
        return;
    case A_PAUSE_QR:
        if (state == RESPONSE || state == THRESHOLD_QR || state == SHARE_QR || state == GROUP_QR) {
            response_paused = !response_paused;
            show();
        }
        return;
    case A_STEP_QR:
        if (state == RESPONSE || state == THRESHOLD_QR || state == SHARE_QR || state == GROUP_QR) {
            response_paused = true;
            response_frame++;
            show();
        }
        return;
    case A_SCAN:
        threshold_restoring = false;
        response_error = 0;
        scan(threshold_loaded() ? SCAN_THRESHOLD : SCAN_REQUEST);
        return;
    case A_RESPONSE_REASON:
        if (state != RESPONSE || !response_error)
            return;
        state = RESPONSE_REASON;
        show();
        return;
    case A_PUBLIC:
        if (state != PUBLIC_TEXT)
            public_return = state;
        state = PUBLIC_IDENTITY;
        show();
        return;
    case A_PUBLIC_TEXT:
        state = PUBLIC_TEXT;
        show();
        return;
    case A_BACKUP:
        state = threshold_loaded() ? SHARE_BACKUP : BACKUP;
        deadline = platform_now() + 600000;
        show();
        return;
    case A_BACKUP_WORDS:
        backup_kind = 2;
        backup_page = 0;
        state = REVEAL_WORDS;
        show();
        return;
    case A_KEY_QR:
        backup_kind = 1;
        state = REVEAL_QR;
        show();
        return;
    case A_BACKUP_NSEC:
        backup_kind = 1;
        state = REVEAL_NSEC;
        show();
        return;
    case A_BACKUP_SEEDQR:
        backup_kind = ns_word_count(core) ? 3 : 1;
        state = REVEAL_QR;
        show();
        return;
    case A_BACKUP_COMPACT:
        backup_kind = 4;
        state = REVEAL_QR;
        show();
        return;
    case A_DETAILS:
        review_index = 0;
        reading_details = true;
        private_offset = 0;
        state = DETAILS;
        reader_done = false;
        show();
        return;
    case A_RESUME_REVIEW:
        reading_details = false;
        state = DECISION;
        show();
        return;
    case A_APPROVE:
        if (state != DECISION)
            return;
        if (partial) {
            state = PARTIAL;
            show();
        } else
            approve(false);
        return;
    case A_PARTIAL_APPROVE:
        if (state == PARTIAL)
            approve(true);
        return;
    case A_SKIP_TEXT:
        if (state == REVIEW && (review_flags & NS_REVIEW_PROSE) &&
            !(review_flags & NS_REVIEW_CRITICAL)) {
            partial = true;
            next_review();
        }
        return;
    case UI_NEXT:
        if (state == WORD_REVIEW) {
            if ((word_review_page + 1) * 4 < word_draft.count)
                word_review_page++;
            else {
                source_kind = 2;
                recover();
                return;
            }
            show();
            return;
        }
        if (state == REVEAL_WORDS) {
            if ((backup_page + 1) * 6 < ns_word_count(core))
                backup_page++;
            else
                state = BACKUP_OPTIONS;
            show();
            return;
        }
        if (state == REVEAL_NSEC || state == REVEAL_QR) {
            state = BACKUP_OPTIONS;
            show();
            return;
        }
        if (state == REVIEW || state == DETAILS) {
            if (!reader_done) {
                if (review_flags & NS_REVIEW_PRIVATE)
                    show();
                return;
            }
            if (state == DETAILS) {
                review_index++;
                reader_done = false;
                private_offset = 0;
                if (review_index >= ns_review_count(core)) {
                    state = DECISION;
                    reading_details = false;
                }
                show();
                return;
            }
            next_review();
            return;
        }
        break;
    case UI_DONE:
        if (state == SHARE_QR) {
            state = BACKUP_OPTIONS;
            show();
            return;
        }
        if (state == RESPONSE || state == RESPONSE_REASON) {
            ns_finish_response(core);
            state = HOME;
            show();
            return;
        }
        if (state == NOTICE) {
            state = notice_return;
            show();
            return;
        }
        ns_cancel(core);
        state = HOME;
        show();
        return;
    default:
        break;
    }
}
void device_scan_bytes(uint8_t *bytes, size_t len) {
    if (state != SCAN || !scanning) {
        platform_wipe(bytes, len);
        return;
    }
    if (scan_target == SCAN_PASSPHRASE) {
        stop_scan();
        char escaped[sizeof(passphrase) * 10 + 1];
        size_t written;
        bool valid = len <= sizeof(passphrase) &&
                     ui_escape_text(bytes, len, escaped, sizeof(escaped), &written);
        platform_wipe(escaped, sizeof(escaped));
        if (!valid) {
            platform_wipe(bytes, len);
            error_message("Use a raw UTF8 passphrase QR of at most 256 bytes.", IDENTITY);
            return;
        }
        platform_wipe(passphrase, sizeof(passphrase));
        memcpy(passphrase, bytes, len);
        passphrase_len = input_len = len;
        platform_wipe(bytes, len);
        private_offset = 0;
        state = PASSPHRASE_REVIEW;
        show();
        return;
    }
    if (scan_target == SCAN_SHARE_IMPORT || scan_target == SCAN_SHARE_CHECK) {
        uint32_t received = ns_frames_received(core);
        int32_t result = scan_target == SCAN_SHARE_IMPORT
                             ? ns_threshold_import_frame(core, bytes, len, platform_now())
                             : ns_threshold_check_backup_frame(core, bytes, len, platform_now());
        platform_wipe(bytes, len);
        if (result == NS_MORE) {
            if (ns_frames_received(core) != received)
                show();
            return;
        }
        stop_scan();
        if (scan_target == SCAN_SHARE_CHECK) {
            state = result == NS_OK ? BACKUP_GOOD : BACKUP_BAD;
            if (result == NS_OK)
                backup_checked = true;
            show();
        } else if (result_ok(result))
            start_review();
        return;
    }
    if (scan_target == SCAN_THRESHOLD) {
        uint32_t received = ns_frames_received(core);
        if (!platform_random32(entropy)) {
            platform_wipe(bytes, len);
            error_message("Random source unavailable. Group operation cancelled.", HOME);
            return;
        }
        int32_t result = ns_threshold_receive_frame(core, bytes, len, entropy, platform_now());
        platform_wipe(bytes, len);
        if (result == NS_MORE) {
            if (ns_frames_received(core) != received)
                show();
            return;
        }
        if (result == NS_OK && ns_threshold_state(core) == NS_THRESHOLD_EXCHANGE &&
            !ns_threshold_output_count(core)) {
            show();
            return;
        }
        stop_scan();
        if (result_ok(result))
            threshold_next();
        return;
    }
    if (scan_target == SCAN_BACKUP_CHECK) {
        stop_scan();
        bool same = len == backup_expected_len;
        unsigned difference = 0;
        if (same)
            for (size_t i = 0; i < len; i++)
                difference |= bytes[i] ^ backup_expected[i];
        platform_wipe(bytes, len);
        state = same && !difference ? BACKUP_GOOD : BACKUP_BAD;
        if (state == BACKUP_GOOD) {
            backup_checked = true;
            platform_wipe(backup_expected, sizeof(backup_expected));
            backup_expected_len = 0;
        }
        show();
        return;
    }
    if (scan_target == SCAN_KEY) {
        stop_scan();
        if (len > sizeof(source)) {
            platform_wipe(bytes, len);
            error_message("This backup is too large.", IMPORT);
            return;
        }
        memcpy(source, bytes, len);
        source_len = len;
        platform_wipe(bytes, len);
        if (len >= 5 && !memcmp(source, "nsec1", 5))
            source_kind = 1;
        else if (len == 16 || len == 20 || len == 24 || len == 28 || len == 32)
            source_kind = 5;
        else {
            bool digits = len > 0;
            for (size_t i = 0; i < len; i++)
                if (source[i] < '0' || source[i] > '9')
                    digits = false;
            source_kind = digits ? 4 : 2;
        }
        finish_identity();
        return;
    }
    uint32_t received = ns_frames_received(core);
    int32_t result = ns_receive_frame(core, bytes, len, platform_now());
    platform_wipe(bytes, len);
    if (result == NS_MORE) {
        if (ns_frames_received(core) != received)
            show();
        return;
    }
    stop_scan();
    if (result != NS_OK) {
        ns_text output;
        if (ns_response(core, &output) == NS_OK) {
            response_error = result;
            response_frame = 0;
            response_paused = false;
            deadline = platform_now() + 120000;
            state = RESPONSE;
            show();
        } else
            error_message(ns_error_text(result), HOME);
        return;
    }
    start_review();
}
void device_scan_error(void) { error_message("Camera stopped. The request was cancelled.", HOME); }
void device_tick(uint64_t now) {
    if (ns_tick(core, now) != NS_OK) {
        stop_scan();
        clear_presentation();
        ns_cancel(core);
        state = HOME;
        show();
        return;
    }
    if ((state == RESPONSE || state == THRESHOLD_QR || state == SHARE_QR || state == GROUP_QR) &&
        !response_paused && now - last_frame >= 800) {
        response_frame++;
        show();
    }
    if (deadline && now >= deadline && (ns_is_loaded(core) || state != HOME)) {
        lock_identity();
        deadline = 0;
        show();
    }
}
bool device_init(void) {
    if (ns_init(core_storage, sizeof(core_storage)) != NS_OK)
        return false;
    platform_new_context();
    state = HOME;
    show();
    return true;
}
void device_emergency_clear(void) {
    platform_wipe(&word_draft, sizeof(word_draft));
    platform_wipe(&quiz, sizeof(quiz));
    platform_wipe(backup_expected, sizeof(backup_expected));
    platform_wipe(core_storage, sizeof(core_storage));
    wipe_inputs();
    platform_wipe(secret_page, sizeof(secret_page));
    platform_wipe(entropy, sizeof(entropy));
    platform_wipe(qr_frame, sizeof(qr_frame));
    platform_wipe(share_backup, sizeof(share_backup));
}
