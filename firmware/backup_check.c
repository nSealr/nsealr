#include "backup_check.h"
#include <string.h>

/* This PRNG only shuffles quiz positions and distractors. It never generates
 * identity material, a nonce or any cryptographic key. */
static uint32_t shuffle_next(backup_check *check) {
    uint32_t value = check->shuffle;
    value ^= value << 13;
    value ^= value >> 17;
    value ^= value << 5;
    check->shuffle = value;
    return value;
}
void backup_check_question(backup_check *check) {
    check->answer = shuffle_next(check) % 4;
    uint16_t correct = check->words[check->order[check->position]];
    for (unsigned i = 0; i < 4; i++) {
        if (i == check->answer) {
            check->choices[i] = correct;
            continue;
        }
        uint16_t candidate;
        bool distinct;
        do {
            candidate = (uint16_t)(shuffle_next(check) % 2048);
            distinct = candidate != correct;
            for (unsigned j = 0; j < i; j++)
                if (check->choices[j] == candidate)
                    distinct = false;
        } while (!distinct);
        check->choices[i] = candidate;
    }
}
bool backup_check_begin(backup_check *check, ns_context *core, const uint8_t random[32]) {
    memset(check, 0, sizeof(*check));
    check->count = ns_word_count(core);
    if (check->count < 12 || check->count > 24)
        return false;
    for (unsigned i = 0; i < 32; i++)
        check->shuffle = (check->shuffle * 33) ^ random[i];
    if (!check->shuffle)
        check->shuffle = 0x9e3779b9;
    uint8_t digits[96] = {0};
    size_t length = 0;
    bool ok =
        ns_backup(core, 3, digits, sizeof(digits), &length) == NS_OK && length == check->count * 4;
    for (unsigned i = 0; i < check->count && ok; i++) {
        unsigned word = 0;
        for (unsigned j = 0; j < 4; j++) {
            uint8_t digit = digits[i * 4 + j];
            if (digit < '0' || digit > '9') {
                ok = false;
                break;
            }
            word = word * 10 + digit - '0';
        }
        if (word >= 2048)
            ok = false;
        check->words[i] = (uint16_t)word;
        check->order[i] = (uint8_t)i;
    }
    volatile uint8_t *wipe = digits;
    for (size_t i = 0; i < sizeof(digits); i++)
        wipe[i] = 0;
    if (!ok)
        return false;
    for (unsigned i = check->count - 1; i > 0; i--) {
        unsigned j = shuffle_next(check) % (i + 1);
        uint8_t temp = check->order[i];
        check->order[i] = check->order[j];
        check->order[j] = temp;
    }
    backup_check_question(check);
    return true;
}
bool backup_check_answer(backup_check *check, unsigned choice) {
    if (choice != check->answer)
        return false;
    if (++check->position < check->count)
        backup_check_question(check);
    return true;
}
