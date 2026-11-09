/* Three public test participants with automatic host consent. This exercises
 * the native optical boundary, not a physical screen or user approval. */
#include "nsealr.h"
#include <stdio.h>
#include <string.h>

static _Alignas(NS_CONTEXT_ALIGN) uint8_t storage[3][NS_CONTEXT_BYTES];
static ns_context *devices[3];
static uint64_t sequence = 0, now = 0;
static uint8_t entropy[32];

static void fresh(void) {
  memset(entropy, 0x42, sizeof(entropy));
  ++sequence;
  memcpy(entropy, &sequence, sizeof(sequence));
  ++now;
}

static int accept(ns_context *device) {
  if (ns_threshold_state(device) != NS_THRESHOLD_REVIEW)
    return NS_OK;
  uint64_t generation = ns_review_generation(device);
  for (uint32_t i = 0; i < ns_review_count(device); ++i) {
    int result = ns_review_seen(device, generation, i);
    if (result != NS_OK)
      return result;
  }
  fresh();
  return ns_approve(device, generation, false, entropy, sizeof(entropy), now);
}

int main(void) {
  int result = NS_OK;
  char line[NS_MAX_FRAME + 16];
  for (unsigned i = 0; i < 3; ++i) {
    result = ns_init(storage[i], sizeof(storage[i]));
    if (result != NS_OK)
      goto done;
    devices[i] = (ns_context *)storage[i];
  }
  while (fgets(line, sizeof(line), stdin)) {
    size_t length = strcspn(line, "\r\n");
    line[length] = 0;
    if (length < 3 || line[0] < '0' || line[0] > '2' || line[1] != ' ') {
      result = -1;
      goto done;
    }
    unsigned member = (unsigned)(line[0] - '0');
    ns_context *device = devices[member];
    fresh();
    if (strcmp(line + 2, "JOIN") == 0) {
      result = ns_threshold_start(device, entropy, now);
    } else {
      result = ns_threshold_receive_frame(device, (const uint8_t *)line + 2,
                                          length - 2, entropy, now);
    }
    if (result == NS_MORE)
      continue;
    if (result != NS_OK || (result = accept(device)) != NS_OK)
      goto done;
    for (uint32_t i = 0; i < ns_threshold_output_count(device); ++i) {
      ns_text output;
      result = ns_threshold_output(device, i, &output);
      if (result != NS_OK)
        goto done;
      if (printf("%u ", member) < 0 ||
          fwrite(output.data, 1, output.len, stdout) != output.len ||
          putchar('\n') == EOF) {
        result = -1;
        goto done;
      }
    }
    ns_finish_response(device);
    if (printf("%u END\n", member) < 0 || fflush(stdout)) {
      result = -1;
      goto done;
    }
  }
done:
  for (unsigned i = 0; i < 3; ++i)
    if (devices[i])
      ns_deinit(devices[i]);
  if (result != NS_OK || ns_heap_reserved()) {
    fprintf(stderr, "Native threshold exchange failed (%d); live=%zu\n", result,
            ns_heap_reserved());
    return 1;
  }
  return 0;
}
