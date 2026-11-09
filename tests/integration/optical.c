/* Public test identity. This exercises the native boundary, not physical
 * review. */
#include "nsealr.h"
#include <stdio.h>
#include <string.h>

static _Alignas(NS_CONTEXT_ALIGN) uint8_t storage[NS_CONTEXT_BYTES];

int main(int argc, char **argv) {
  bool session = argc == 2 && strcmp(argv[1], "--session") == 0;
  if (argc != 1 && !session)
    return 1;
  ns_context *ctx = (ns_context *)storage;
  uint8_t entropy[32] = {0};
  char frame[NS_MAX_FRAME + 3];
  if (ns_init(storage, sizeof(storage)))
    return 1;
  entropy[31] = 3;
  if (ns_generate(ctx, 0, entropy, NULL, 0, 0))
    return 1;
  uint64_t now = 1;
  uint64_t sequence = 0;
  do {
    bool complete = false;
    while (fgets(frame, sizeof(frame), stdin)) {
      size_t len = strcspn(frame, "\r\n");
      int result = ns_receive_frame(ctx, (uint8_t *)frame, len, now++);
      if (result < 0) {
        fprintf(stderr, "Request rejected: %s\n", ns_error_text(result));
        ns_deinit(ctx);
        return 2;
      }
      if (result == NS_OK) {
        complete = true;
        break;
      }
    }
    if (!complete) {
      ns_deinit(ctx);
      return session && sequence ? 0 : 3;
    }
    uint64_t generation = ns_review_generation(ctx);
    for (uint32_t i = 0; i < ns_review_count(ctx); ++i) {
      ns_text label, value;
      uint32_t flags;
      if (ns_review_item(ctx, i, &label, &value, &flags) || !label.len ||
          ns_review_seen(ctx, generation, i))
        return 1;
    }
    memset(entropy, 0x42, sizeof(entropy));
    ++sequence;
    memcpy(entropy, &sequence, sizeof(sequence));
    if (ns_approve(ctx, generation, false, entropy, sizeof(entropy), now++))
      return 1;
    ns_text response;
    if (ns_response(ctx, &response))
      return 1;
    size_t count = (response.len + NS_QR_CHUNK - 1) / NS_QR_CHUNK;
    for (size_t i = 0; i < count; ++i) {
      size_t written;
      if (ns_encode_frame(response.data, response.len, i, (uint8_t *)frame,
                          sizeof(frame), &written))
        return 1;
      if (fwrite(frame, 1, written, stdout) != written || putchar('\n') == EOF)
        return 1;
    }
    if (fflush(stdout))
      return 1;
    ns_finish_response(ctx);
  } while (session);
  ns_deinit(ctx);
  if (ns_heap_reserved())
    return 1;
  return 0;
}
