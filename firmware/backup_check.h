#ifndef NSEALR_BACKUP_CHECK_H
#define NSEALR_BACKUP_CHECK_H
#include "nsealr.h"
#include <stdbool.h>
typedef struct {
    uint16_t words[24], choices[4];
    uint8_t order[24];
    unsigned count, position, answer;
    uint32_t shuffle;
} backup_check;
bool backup_check_begin(backup_check *check, ns_context *core, const uint8_t random[32]);
bool backup_check_answer(backup_check *check, unsigned choice);
void backup_check_question(backup_check *check);
#endif
