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
    for (unsigned i = 0; i < check->count; i++) {
        if (ns_backup_word_index(core, i, &check->words[i]) != NS_OK) {
            memset(check, 0, sizeof(*check));
            return false;
        }
        check->order[i] = (uint8_t)i;
    }
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
