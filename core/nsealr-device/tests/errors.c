/* Failed semantic requests still reach their waiting client as NIP46 errors. */
#include "nsealr.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static _Alignas(NS_CONTEXT_ALIGN) uint8_t storage[NS_CONTEXT_BYTES];
int main(void) {
  ns_context *ctx = (ns_context *)storage;
  uint8_t entropy[32] = {3}, frame[NS_MAX_FRAME];
  const char request[] =
      "{\"id\":\"refused-client\",\"method\":\"unsupported\",\"params\":[]}";
  size_t length;
  ns_text response;
  assert(ns_init(storage, sizeof(storage)) == NS_OK);
  assert(ns_generate(ctx, 0, entropy, NULL, 0, 0) == NS_OK);
  assert(ns_encode_frame((const uint8_t *)request, strlen(request), 0, frame,
                         sizeof(frame), &length) == NS_OK);
  for (unsigned scenario = 0; scenario < 3; ++scenario) {
    assert(ns_receive_frame(ctx, frame, length, 1) < 0);
    assert(ns_review_count(ctx) == 0);
    assert(ns_response(ctx, &response) == NS_OK);
    assert(response.len ==
           strlen("{\"id\":\"refused-client\",\"error\":\"Unsupported "
                  "operation or event semantics\"}"));
    assert(memcmp(response.data,
                  "{\"id\":\"refused-client\",\"error\":\"Unsupported "
                  "operation or event semantics\"}",
                  response.len) == 0);
    memset(entropy, 4, sizeof(entropy));
    assert(ns_approve(ctx, ns_review_generation(ctx), false, entropy,
                      sizeof(entropy), 1) < 0);
    for (size_t i = 0; i < sizeof(entropy); ++i)
      assert(entropy[i] == 0);
    if (scenario == 0)
      ns_finish_response(ctx);
    if (scenario == 1)
      assert(ns_receive_frame(ctx, (const uint8_t *)"invalid", 7, 1) < 0);
    if (scenario == 2)
      assert(ns_receive_frame(ctx, frame, NS_MAX_MESSAGE + 1, 1) < 0);
    assert(ns_response(ctx, &response) < 0);
  }
  ns_deinit(ctx);
  assert(ns_heap_reserved() == 0);
  puts("PASS optical error binding, malformed replacement, bounds and stale "
       "approval");
  return 0;
}
