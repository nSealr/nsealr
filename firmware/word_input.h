#ifndef NSEALR_WORD_INPUT_H
#define NSEALR_WORD_INPUT_H
#include "nsealr.h"
#include <stdbool.h>
#include <stdint.h>

typedef struct {
    uint16_t words[24], matches[2048];
    uint8_t prefix[9];
    unsigned count, position, prefix_len, match_count, match_page;
} word_input;
void words_begin(word_input *input, unsigned count);
void words_edit(word_input *input, unsigned position);
void words_type(word_input *input, unsigned letter);
void words_erase(word_input *input);
uint32_t words_valid_letters(const word_input *input);
bool words_choose(word_input *input, unsigned visible_choice);
bool words_assemble(const word_input *input, uint8_t *out, size_t cap, size_t *written);
#endif
