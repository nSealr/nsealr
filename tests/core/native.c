#include "nsealr.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

static _Alignas(NS_CONTEXT_ALIGN) uint8_t storage[NS_CONTEXT_BYTES];
static ns_context *ctx = (ns_context *)storage;
static uint8_t output[NS_MAX_MESSAGE], backup[256], entropy[32];
static char request[NS_MAX_MESSAGE], original_key[64];
static size_t written;

static void zero(const uint8_t *bytes, size_t len) {
    for (size_t i = 0; i < len; ++i) assert(bytes[i] == 0);
}
static void review_all(void) {
    uint64_t generation = ns_review_generation(ctx);
    for (uint32_t i = 0; i < ns_review_count(ctx); ++i) {
        ns_text label, value; uint32_t flags;
        assert(ns_review_item(ctx, i, &label, &value, &flags) == 0);
        assert(label.len > 0);
        assert(ns_review_seen(ctx, generation, i) == 0);
    }
}
int main(void) {
    assert(ns_init(storage, sizeof(storage)) == 0);
    assert(!ns_is_loaded(ctx));
    memset(entropy, 0, sizeof(entropy)); entropy[31] = 3;
    assert(ns_generate(ctx, 0, entropy, NULL, 0, 0) == 0);
    zero(entropy, sizeof(entropy));
    assert(ns_public_key(ctx, 0, output, sizeof(output), &written) == 0);
    assert(written == 64);
    assert(memcmp(output, "f9308a019258c31049344f85f89d5229b531c845836f99b08601f113bce036f9", 64) == 0);
    memcpy(original_key, output, 64);
    assert(ns_backup(ctx, 1, backup, sizeof(backup), &written) == 0);
    ns_lock(ctx); assert(!ns_is_loaded(ctx));
    assert(ns_import_nsec(ctx, backup, written) == 0); zero(backup, sizeof(backup));

    int n = snprintf(request, sizeof(request),
        "{\"id\":\"c-test\",\"method\":\"sign_event\",\"params\":[\"{\\\"pubkey\\\":\\\"%.*s\\\",\\\"created_at\\\":0,\\\"kind\\\":1,\\\"tags\\\":[],\\\"content\\\":\\\"\\\"}\"]}",
        64, original_key);
    assert(n > 0 && (size_t)n < sizeof(request));
    assert(ns_request(ctx, (uint8_t *)request, (size_t)n, 1) == 0);
    uint64_t generation = ns_review_generation(ctx);
    memset(entropy, 4, sizeof(entropy));
    assert(ns_approve(ctx, generation, true, entropy, sizeof(entropy), 2) < 0);
    zero(entropy, sizeof(entropy));
    assert(ns_review_count(ctx) == 0);
    assert(ns_request(ctx, (uint8_t *)request, (size_t)n, 3) == 0);
    assert(ns_request(ctx, (uint8_t *)request, NS_MAX_MESSAGE + 1, 3) < 0);
    assert(ns_review_count(ctx) == 0);
    assert(ns_request(ctx, (uint8_t *)request, (size_t)n, 3) == 0);
    review_all(); generation = ns_review_generation(ctx);
    memset(entropy, 0, sizeof(entropy));
    assert(ns_approve(ctx, generation, false, entropy, sizeof(entropy), 4) == 0);
    ns_text response; assert(ns_response(ctx, &response) == 0);
    assert(response.len < NS_MAX_MESSAGE);
    /* Independent upstream BIP340 vector for scalar3, empty kind1 at time0. */
    const char *id = "543196f25ef9ed178a696cd3927d23245605680642cef2c2f9d57cd622c0ed7c";
    memcpy(output, response.data, response.len); output[response.len] = 0;
    assert(strstr((char *)output, id) != NULL);
    assert(ns_encode_frame(response.data, response.len, 0, backup, sizeof(backup), &written) < 0);
    assert(ns_encode_frame(response.data, response.len, 0, output, sizeof(output), &written) == 0);
    assert(written <= NS_MAX_FRAME && memcmp(output, "ns:", 3) == 0);
    assert(ns_approve(ctx, generation, false, entropy, sizeof(entropy), 5) < 0);
    ns_cancel(ctx); assert(ns_response(ctx, &response) < 0);

    /* Exercise the supported 8192-byte prose and 256-tag boundary in the same
     * bounded native allocation domain used by the target staticlib. */
    size_t offset = (size_t)snprintf(request, sizeof(request),
        "{\"id\":\"large\",\"method\":\"sign_event\",\"params\":[\"{\\\"pubkey\\\":\\\"%.*s\\\",\\\"created_at\\\":1,\\\"kind\\\":1,\\\"tags\\\":[",64,original_key);
    for (int i = 0; i < 256; ++i) {
        offset += (size_t)snprintf(request + offset, sizeof(request) - offset,
                                  "%s[\\\"t\\\",\\\"example\\\"]", i ? "," : "");
    }
    offset += (size_t)snprintf(request + offset, sizeof(request) - offset, "],\\\"content\\\":\\\"");
    memset(request + offset, 'a', 8192); offset += 8192;
    offset += (size_t)snprintf(request + offset, sizeof(request) - offset, "\\\"}\"]}");
    assert(offset < sizeof(request));
    assert(ns_request(ctx, (uint8_t *)request, offset, 10) == 0);
    review_all(); generation = ns_review_generation(ctx);
    memset(entropy, 7, sizeof(entropy));
    assert(ns_approve(ctx, generation, false, entropy, sizeof(entropy), 11) == 0);
    assert(ns_response(ctx, &response) == 0 && response.len < NS_MAX_MESSAGE);
    ns_lock(ctx); assert(!ns_is_loaded(ctx));

    memset(entropy, 7, sizeof(entropy));
    uint8_t passphrase[] = "TREZOR";
    assert(ns_generate(ctx, 24, entropy, passphrase, sizeof(passphrase)-1, 1) == 0);
    zero(entropy, sizeof(entropy)); zero(passphrase, sizeof(passphrase)-1);
    assert(ns_word_count(ctx) == 24);
    assert(ns_backup(ctx, 4, backup, sizeof(backup), &written) == 0 && written == 32);
    assert(ns_public_key(ctx, 0, output, sizeof(output), &written) == 0);
    memcpy(original_key, output, 64);
    ns_lock(ctx);
    memcpy(passphrase, "TREZOR", 6);
    assert(ns_import_secret_qr(ctx, 3, backup, 32, passphrase, 6, 1) == 0);
    zero(backup, sizeof(backup)); zero(passphrase, 6);
    assert(ns_public_key(ctx, 0, output, sizeof(output), &written) == 0);
    assert(memcmp(original_key, output, 64) == 0);
    ns_deinit(ctx); zero(storage, sizeof(storage));
    printf("PASS native identity/recovery/review/sign/QR/lock; heap peak=%zu live=%zu\n", ns_heap_peak(), ns_heap_reserved());
    return 0;
}
