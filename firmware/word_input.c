#include "word_input.h"
#include <string.h>

static void find_matches(word_input *input) {
    size_t found = 0;
    if (input->prefix_len &&
        ns_wordlist_find(input->prefix, input->prefix_len, input->matches, 2048, &found) != NS_OK)
        found = 0;
    input->match_count = (unsigned)found;
    input->match_page = 0;
}
void words_begin(word_input *input, unsigned count) {
    memset(input, 0, sizeof(*input));
    input->count = count;
    for (unsigned i = 0; i < 24; i++)
        input->words[i] = UINT16_MAX;
}
void words_edit(word_input *input, unsigned position) {
    if (position >= input->count)
        return;
    input->position = position;
    input->prefix_len = 0;
    memset(input->prefix, 0, sizeof(input->prefix));
    if (input->words[position] != UINT16_MAX) {
        ns_text word;
        if (ns_wordlist_word(input->words[position], &word) == NS_OK && word.len <= 8) {
            memcpy(input->prefix, word.data, word.len);
            input->prefix_len = (unsigned)word.len;
        }
    }
    find_matches(input);
}
void words_type(word_input *input, unsigned letter) {
    if (letter < 'a' || letter > 'z' || input->prefix_len >= 8)
        return;
    input->prefix[input->prefix_len++] = (uint8_t)letter;
    find_matches(input);
    if (!input->match_count) {
        input->prefix[--input->prefix_len] = 0;
        find_matches(input);
    }
}
void words_erase(word_input *input) {
    if (input->prefix_len)
        input->prefix[--input->prefix_len] = 0;
    find_matches(input);
}
uint32_t words_valid_letters(const word_input *input) {
    if (!input->prefix_len)
        return (1u << 26) - 1;
    uint32_t valid = 0;
    for (unsigned i = 0; i < input->match_count; i++) {
        ns_text word;
        if (ns_wordlist_word(input->matches[i], &word) == NS_OK && word.len > input->prefix_len)
            valid |= 1u << (word.data[input->prefix_len] - 'a');
    }
    return valid;
}
bool words_choose(word_input *input, unsigned visible_choice) {
    unsigned index = input->match_page + visible_choice;
    if (input->prefix_len < 2 || visible_choice >= 2 || index >= input->match_count)
        return false;
    input->words[input->position] = input->matches[index];
    return true;
}
bool words_assemble(const word_input *input, uint8_t *out, size_t cap, size_t *written) {
    size_t at = 0;
    if (!input || !out || !written || input->count < 12 || input->count > 24)
        return false;
    for (unsigned i = 0; i < input->count; i++) {
        ns_text word;
        if (input->words[i] == UINT16_MAX || ns_wordlist_word(input->words[i], &word) != NS_OK)
            return false;
        if (word.len + (i ? 1 : 0) > cap - at)
            return false;
        if (i)
            out[at++] = ' ';
        memcpy(out + at, word.data, word.len);
        at += word.len;
    }
    *written = at;
    return true;
}
