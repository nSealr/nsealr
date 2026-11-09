#ifndef NSEALR_H
#define NSEALR_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

/* One serialized caller owns this storage. No concurrent or reentrant calls.
 * Every pointer/length describes a live allocation; mutable buffers must not
 * overlap each other or context storage. Deinitialize before reinitializing. */
#define NS_CONTEXT_BYTES 2048u
#define NS_CONTEXT_ALIGN 16u
#define NS_MAX_MESSAGE 32768u
#define NS_MAX_CONTENT 8192u
#define NS_QR_CHUNK 384u
#define NS_MAX_FRAMES 86u
#define NS_MAX_FRAME 586u
#define NS_REVIEW_CRITICAL 1u
#define NS_REVIEW_PROSE 2u
#define NS_REVIEW_DETAIL 4u
#define NS_REVIEW_PRIVATE 8u
#define NS_OK 0
#define NS_MORE 1

typedef struct ns_context ns_context;
typedef struct { const uint8_t *data; size_t len; } ns_text;

/* All returned slices expire on the next mutating call. They are never secrets
 * except reviewed private plaintext; do not log or persist them. */
int32_t ns_init(void *storage, size_t bytes);
void ns_deinit(ns_context *ctx);
void ns_lock(ns_context *ctx);
void ns_cancel(ns_context *ctx);
/* Dismiss completed output, retaining bounded private-message continuations.
 * If review or collection is pending this cancels everything instead. */
void ns_finish_response(ns_context *ctx);
/* Monotonic event-loop cleanup: 0 unchanged, 1 expired, negative clock/error.
 * On nonzero clear rendered private/review/output text; identity stays loaded. */
int32_t ns_tick(ns_context *ctx, uint64_t now_ms);
bool ns_is_loaded(const ns_context *ctx);
const char *ns_error_text(int32_t error);

/* Secret input/passphrase/entropy buffers are wiped on success and failure.
 * Nsec has no passphrase/account. English mnemonic imports accept 12/15/18/21/24.
 * Local QR kind: 1=nsec, 2=standard SeedQR digits, 3=compact SeedQR bytes. */
int32_t ns_import_nsec(ns_context *ctx, uint8_t *input, size_t len);
int32_t ns_import_mnemonic(ns_context *ctx, uint8_t *input, size_t len,
                         uint8_t *passphrase, size_t passphrase_len, uint32_t account);
int32_t ns_import_secret_qr(ns_context *ctx, uint32_t kind, uint8_t *input, size_t len,
                          uint8_t *passphrase, size_t passphrase_len, uint32_t account);
/* words=0 creates a raw nsec from entropy32; words=12/24 creates a mnemonic.
 * The platform must qualify entropy before calling. Never use fixture entropy. */
int32_t ns_generate(ns_context *ctx, uint32_t words, uint8_t entropy32[32],
                    uint8_t *passphrase, size_t passphrase_len, uint32_t account);
/* Local generation, initially without a passphrase at account0. Dice requires
 * exactly50/100 ASCII digits1..6 for12/24 words. SHA256 of the exact digits is
 * deterministic; hashing does not compensate for biased or dependent rolls.
 * Photo input is SHA256(domain || image_digest32 || hardware_entropy32).
 * The platform owns capture/consent and source qualification. All inputs wipe. */
int32_t ns_generate_dice(ns_context *ctx, uint32_t words, uint8_t *rolls, size_t len);
int32_t ns_generate_photo(ns_context *ctx, uint32_t words,
                          uint8_t image_digest32[32], uint8_t hardware_entropy32[32]);
/* Check English BIP39 words/checksum without deriving or replacing an identity.
 * The input is wiped on success and failure. */
int32_t ns_validate_mnemonic(uint8_t *input, size_t len);
/* public format: 0=64-byte hex, 1=npub. Output is not NUL-terminated. */
int32_t ns_public_key(const ns_context *ctx, uint32_t format,
                     uint8_t *out, size_t capacity, size_t *written);
uint32_t ns_word_count(const ns_context *ctx);
int32_t ns_wordlist_word(uint32_t index, ns_text *word);
int32_t ns_wordlist_find(const uint8_t *prefix, size_t len,
                        uint16_t *indices, size_t capacity, size_t *written);
/* Local physical backup consent is mandatory before these calls. No network
 * method reaches them. Caller clears the entire output and display on exit.
 * Backup kind: 1=nsec, 2=mnemonic, 3=standard SeedQR, 4=compact SeedQR. */
int32_t ns_backup(const ns_context *ctx, uint32_t kind,
                 uint8_t *out, size_t capacity, size_t *written);
int32_t ns_backup_word(const ns_context *ctx, uint32_t index,
                      uint8_t *out, size_t capacity, size_t *written);
/* Local backup/quiz only; works for every supported mnemonic length.
 * The caller wipes the returned secret index. Output is zero on failure. */
int32_t ns_backup_word_index(const ns_context *ctx, uint32_t index, uint16_t *out);

/* Scan an ordinary request before loading an identity. No review authority is
 * created. NS_MORE means more frames; NS_OK means a complete staged request.
 * Local key imports preserve it. Cancel, Lock, invalid input and expiry clear it.
 * Resume consumes it once, checks the loaded identity and starts fresh review;
 * the original ten-minute scan deadline also bounds that review. */
int32_t ns_stage_frame(ns_context *ctx, const uint8_t *frame, size_t len, uint64_t now_ms);
bool ns_has_staged_request(const ns_context *ctx);
int32_t ns_resume_request(ns_context *ctx, uint64_t now_ms);

/* Replacing a request cancels old authority. now_ms is trusted monotonic time.
 * Each request expires after ten minutes. Frame intake returns NS_MORE until
 * complete; it verifies exact lengths/hash before invoking request parsing.
 * On a negative result, ns_response may hold an id-bound error for the client.
 * Malformed or unidentified input has no response; never approve a failed request. */
int32_t ns_request(ns_context *ctx, const uint8_t *json, size_t len, uint64_t now_ms);
int32_t ns_receive_frame(ns_context *ctx, const uint8_t *frame, size_t len, uint64_t now_ms);
uint32_t ns_frames_received(const ns_context *ctx);
uint32_t ns_frames_expected(const ns_context *ctx);
uint64_t ns_review_generation(const ns_context *ctx);
uint32_t ns_review_count(const ns_context *ctx);
/* Use this action label for final consent. List replacement approves the whole
 * displayed count and effect; optional DETAIL entries are not marked as read. */
int32_t ns_review_confirmation(const ns_context *ctx, ns_text *label);
int32_t ns_review_item(const ns_context *ctx, uint32_t index,
                      ns_text *label, ns_text *value, uint32_t *flags);
/* Mark only after the complete item was actually presented. Rendering a prefix
 * is not completion. CRITICAL fields cannot be skipped by partial approval. */
int32_t ns_review_seen(ns_context *ctx, uint64_t generation, uint32_t index);
/* Explicit local partial_prose applies to this request only. Pending authority
 * is consumed before signing/encryption; failures cannot be retried. Fresh
 * entropy32 is required for sign/encrypt and wiped for every outcome. */
int32_t ns_approve(ns_context *ctx, uint64_t generation, bool partial_prose,
                  uint8_t *entropy32, size_t entropy_len, uint64_t now_ms);
int32_t ns_reject(ns_context *ctx, uint64_t generation);
int32_t ns_response(const ns_context *ctx, ns_text *json);
int32_t ns_encode_frame(const uint8_t *message, size_t len, uint32_t index,
                       uint8_t *out, size_t capacity, size_t *written);

/* Local 2-of-3 custody. These are deliberate device actions, not NIP46 methods.
 * Same QR framing and common review/approve/reject/cancel/tick APIs as above.
 * Setup confirms the complete matching roster fingerprint on all three devices.
 * Only authenticated encrypted peer packets reach the companion. */
#define NS_THRESHOLD_NONE 0u
#define NS_THRESHOLD_JOIN 1u
#define NS_THRESHOLD_REVIEW 2u
#define NS_THRESHOLD_EXCHANGE 3u
#define NS_THRESHOLD_READY 4u
#define NS_THRESHOLD_RESULT 5u
#define NS_THRESHOLD_MAX_BACKUP 2048u
int32_t ns_threshold_start(ns_context *ctx, uint8_t entropy32[32], uint64_t now_ms);
int32_t ns_threshold_receive(ns_context *ctx, const uint8_t *json, size_t len,
                             uint8_t entropy32[32], uint64_t now_ms);
int32_t ns_threshold_receive_frame(ns_context *ctx, const uint8_t *frame, size_t len,
                                   uint8_t entropy32[32], uint64_t now_ms);
uint32_t ns_threshold_state(const ns_context *ctx);
/* Received peer messages in the current exchange, always 0..2. */
uint32_t ns_threshold_progress(const ns_context *ctx);
uint32_t ns_threshold_output_count(const ns_context *ctx);
int32_t ns_threshold_output(const ns_context *ctx, uint32_t index, ns_text *json);
/* Secret share backup is a distinct checksummed QR format, never mnemonic/nsec.
 * Export requires deliberate local backup consent; no network action reaches it.
 * Import wipes input, then requires displayed group/member confirmation. */
int32_t ns_threshold_backup(const ns_context *ctx, uint8_t *out, size_t capacity, size_t *written);
int32_t ns_threshold_import(ns_context *ctx, uint8_t *backup, size_t len, uint64_t now_ms);
/* Local secret animation: same framing, at most2048 assembled bytes. Frame
 * input is wiped. Restore completion starts review; check keeps the loaded share.
 * Neither API exposes backup contents through ordinary request/result outputs. */
int32_t ns_threshold_import_frame(ns_context *ctx, uint8_t *frame, size_t len, uint64_t now_ms);
int32_t ns_threshold_check_backup_frame(ns_context *ctx, uint8_t *frame, size_t len, uint64_t now_ms);
/* Public record for independent recovery checks; member is 1..3. */
int32_t ns_threshold_info(const ns_context *ctx, uint8_t group_hex[64], uint32_t *member);
/* Same public nsealr_group JSON as setup completion;1024 bytes suffice.
 * Does not change pending state. Output is cleared on failure; no NUL added. */
int32_t ns_threshold_record(const ns_context *ctx, uint8_t *out, size_t capacity, size_t *written);
/* Lost-share repair uses start/join on the replacement and normal receive/review
 * on the two loaded helpers. nsealr_repair binds the old public descriptor,
 * stable roster members:[{id:1,key:hex},...], lost participant and replacement key.
 * Repair preserves npub; it does not revoke copies of the original share.
 * The replacement emits2 ready peer packets then its group record (3 outputs).
 * Each helper emits its new record after receiving its ready packet. Keep old
 * backups until all3 records agree, then save updated share backups. */

/* Bare-metal staticlib hooks: internal RAM only, correct alignment, no unwind.
 * Rust wraps every allocation in a bounded wipe-before-free allocator. OOM or
 * panic is fatal; abort must stop signing and reset into a locked session. */
void *ns_platform_alloc(size_t size, size_t align);
void ns_platform_free(void *ptr, size_t size, size_t align);
_Noreturn void ns_platform_abort(void);
size_t ns_heap_reserved(void);
size_t ns_heap_peak(void);
#endif
