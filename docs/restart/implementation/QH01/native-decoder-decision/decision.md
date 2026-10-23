# Two Rust QR decoders: source-only resource decision

**NO for the complete thin-wrapper contract with these pinned public APIs.**
Neither release supplies per-call enforcement of caller-declared allocation and
work budgets throughout image detection and decoding. Pixel/dimension preflight
is useful, and `rqrr` exposes a bounded-output seam, but those are partial
properties. This packet does not establish a complete conservative resource bound
for all admitted images, or prove that deriving one is mathematically impossible.
Neither decoder is selected or admitted as an already resource-bounded scanner.

The scope is exactly `quircs 0.10.3` and `rqrr 0.11.0`, source archives retrieved
and pinned on 20 October, completed from the saved sources on 23 October 2026.
The repo input remains accepted `0985af3a3e2aab335eaaeac09a3b3f1fd0bd1ebf`.
Original WIP `6a082647d289f16762449c5c81a2fe8f88d484ef`, its pause record and
export-helper error remain historical; this is an authored decision awaiting
root's distinct source review. There were no crate builds, decoder runs, new
fixtures/tests, dependency resolutions, backend changes or CI observations.

| Fixed input | Published metadata | Reviewed archive SHA256 | Source requirements |
| --- | --- | --- | --- |
| quircs 0.10.3 | [Official release](https://crates.io/api/v1/crates/quircs/0.10.3) | `d71dee9e56835add6f9c26227e6c690b19eda9414f5affc666c3ec833ba140dc` | Edition 2018; declared Rust 1.68; no feature switches |
| rqrr 0.11.0 | [Official release](https://crates.io/api/v1/crates/rqrr/0.11.0) | `8d084c50c5cfa397a081850da329566c8667b0b6c4e81da16abff1fef27de93b` | Edition 2021; declared Rust 1.85.1; default `img` enables optional `image` |

[Source pins](source-pins.json) retain the official metadata, resolved download
URLs, checksums, dependency declarations and notices. The archive's upstream
commit fields are publisher declarations, not a separately verified Git tree.
The reviewed identities are the checksum-matched official crate archives.
[Quircs evidence](evidence/quircs-source.json) and
[rqrr evidence](evidence/rqrr-source.json) retain 33 exact source slices, original
file/range identities and hashes. References below name those slice IDs.

A wrapper can reject zero/excess dimensions, check products and strides without
overflow, and validate the required source length before calling either library.
For `quircs`, the input is contiguous 8-bit luminance with exactly width*height
bytes. Its `identify` calls `resize` before asserting that length, so the wrapper
must perform its own precheck before allocation. Neither the input pixel count
nor a successful checked multiplication proves the safety/cost of every later
projective-coordinate operation. Encoded PNG/JPEG parsing, capture and pixel
conversion are separate allocation/work boundaries, not covered by a check
performed after an image has already been expanded.

| Property | quircs 0.10.3 | rqrr 0.11.0 |
| --- | --- | --- |
| Input dimension/pixel preflight | Possible before construction/identify; not a complete internal resource bound | Possible before public raw constructors; not a complete internal resource bound |
| Caller output-storage ceiling before appending | No writer/limit argument; payload Vec is constructed first | `Grid::decode_to(Write)` exposes a fallible output seam; a future fixed-capacity writer must discard all partial output on any error |
| All internal heap/state growth under a caller byte budget | No per-call allocator/budget API | No per-call allocator/budget API |
| All detection/ECC work under a caller meter/deadline | No complete meter or cancellation hook | No complete meter or cancellation hook |
| `no_std`/alloc-only support as shipped | No; uses std and heap | No; disabling `img` does not remove std or heap |

`quircs` takes the eager path `Quirc::identify` → `resize` → threshold/pixel setup
→ every-row finder scan → grouping, and only then returns `CodeIter`
(`quircs-eager-identify`). Taking one iterator result cannot limit the detection
already completed. `Quirc::default` allocates initial region/capstone/grid
capacities; `resize` grows the pixel Vec using unchecked width*height, and reset
clears state Vec lengths without dropping their capacity
(`quircs-state-default-resize`). The library has genuine fixed count guards:
65,534 region entries including reserved entries, 32 capstones and eight grids
(`quircs-region-cap`, `quircs-capstone-cap`, `quircs-grid-cap`). Those are library
counts, not a caller's permitted heap size, retained-capacity measurement or
physical profile capacity.

The same detector creates a local growing Vec for flood seeds and executes
geometry-derived alignment spirals (`quircs-flood-heap`,
`quircs-alignment-spiral`). Fixed capstone counts constrain some later loops;
they do not charge all work to a caller budget. Signed geometric products and
coordinate conversions require additional arithmetic reasoning
(`quircs-integer-geometry`). The source also uses unchecked pixel accesses under
its invariants. This packet reports no executed overflow, exploit, endless loop
or general memory-safety finding.

`Code::decode` then creates a datastream containing two 8,896-byte arrays,
checks grid size/version, tries two format locations, corrects ECC and constructs
`Data.payload` (`quircs-payload-array`, `quircs-decode-entry`). Numeric, byte and
Kanji paths check the library's logical overflow threshold before growing that
Vec (`quircs-numeric-growth`, `quircs-byte-growth`, `quircs-kanji-growth`). That
threshold is not a caller's smaller envelope limit, allocator capacity or total
live scratch storage. Checking the returned payload length cannot provide the
missing cap before its internal output allocation.

`rqrr` takes `PreparedImage::prepare_from_*` → preparation → `detect_grids` →
capstone detection → neighbor ranking/group trials → locations/result Vec.
The public raw constructors use checked width*height, but overflow is an `expect`
panic and successful calls allocate library-owned Vec/Box storage
(`rqrr-checked-constructors`). `prepare` additionally allocates row averages and
an LRU with logical capacity 251 (`rqrr-prepare`). **ImageBuffer is not a public
customization seam for an external no-img wrapper:** the trait is inside private
`mod prepare` and is not re-exported. The public helpers remain available; the
optional `img` feature supplies a blanket implementation for image traits
(`rqrr-std-reference`, `rqrr-clone-and-buffer`). This corrects the WIP's stronger
claim, without changing the full-contract NO; see
[the preserved precision revision](evidence/resume-precision.json).

Detection collects capstones, builds and sorts candidate pair vectors, and clones
`PreparedImage` for each trial grouping (`rqrr-uncapped-capstone-vector`,
`rqrr-pair-vector-and-sort`, `rqrr-eager-detection-and-clone`). For the helpers'
`BasicImageBuffer`, derived Clone duplicates boxed pixel storage; PreparedImage
also constructs/copies its cache. Trial clones are temporary, not all retained
simultaneously. Cumulative allocation/work and peak retained storage are distinct
obligations. The 251-entry cache can evict/repaint regions; a separate flood queue
grows internally (`rqrr-cache-repaint`, `rqrr-flood-heap`). Finite image dimensions
bound the input domain, but the API has no caller cap covering all these structures
before growth. Truncating the returned grid Vec is too late.

Alignment spirals, projective assertions and signed geometry are additional work
and arithmetic paths, not covered by a decoded-output counter
(`rqrr-alignment-spiral`, `rqrr-perspective-asserts`, `rqrr-integer-geometry`).
Even a pixel-access counter would not meter all pair ranking, geometry and ECC;
the internal ImageBuffer trait is not directly implementable externally anyway.
Panicking callbacks, a dropped future or a timeout returning to its caller are
not a demonstrated recoverable allocation cap or cancellation of a synchronous
library operation. No such workaround or isolation architecture is selected here.

`Grid::decode_to` is the meaningful positive difference. The caller supplies
`std::io::Write`; byte/other payload writes can fail before copying beyond a
fixed destination (`rqrr-writer-api`, `rqrr-byte-writer`). Partial output is
explicitly possible and must be discarded on every error, never handed to the
envelope parser. The convenience `decode` instead collects Vec then String.
Raw extraction/ECC uses fixed 8,896-byte arrays and at most a normal attempt plus
one mirrored attempt before payload writing (`rqrr-raw-array`, `rqrr-ECC-array`,
`rqrr-mirrored-retry`). A writer error does not restart mirrored output. These
are source properties, not an implemented wrapper, total stack bound or work
budget. The computed version check 1..40 is not a proof of all legal BitGrid
geometry preconditions; public `SimpleGrid::from_func` also allocates from an
unchecked size product (`rqrr-workspace-and-version`, `rqrr-simple-grid-allocation`).

Both releases require std and heap as shipped. `quircs` declares normal
num-derive/num-traits/thiserror dependencies (derive macros act at build time) and
dev-only image. `rqrr` retains normal g2p/lru dependencies without `img`; disabling that feature removes the optional image
adapter, not std::io, std::error, Vec, Box or LRU. No dependency lock was selected.
The repo's existing Rust 1.95.0 is above the declared MSRVs; this does not establish
a build, ABI, no_std, bare-metal, ARM/Pi or target memory/stack result. Allocator
failure behavior and actual target stack/heap are unqualified.

Licensing is also source-bound, not cleared by this packet. `quircs` metadata and
Cargo declare MIT, while its delivered LICENSE contains the ISC-style grant and
disclaimer. Both are preserved and the discrepancy remains unreconciled.
`rqrr` declares `(MIT OR Apache-2.0) AND ISC` and includes all three notices;
its README's MIT/Apache summary alone omits ISC. Exact notices and hashes are
retained in [licenses](licenses/) and source pins.

The minimum missing result is a reviewed enforcement boundary covering all
relevant internal allocations/work before they occur, or a complete conservative
admission bound covering every admitted image, geometry/arithmetic precondition,
allocator growth policy and target storage requirement before the whole call.
Neither API supplies the former; this source packet does not provide the latter.
A four-image benchmark or observed peak/time cannot prove that all-input property.
The decision therefore stops at NO for the complete thin-wrapper contract.

[Existing asset references](existing-asset-references.json) bind the frozen13949
public images/envelopes and distinct host review89280 without copying a corpus.
Their ZBar image result is not a quircs/rqrr functional or resource experiment.
All five QH01 criteria remain incomplete. No native scanner, framing freeze,
physical capacity, manual-port limit reinterpretation, consent or key authority
is introduced. The sole graph and all app/runtime/lock/vendor/CI files are unchanged.
