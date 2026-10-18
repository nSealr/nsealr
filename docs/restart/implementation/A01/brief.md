# A01 — Source, consumer and repository-disposition brief

Author: `/root`. Input: the source pins in `repository-observations.json`, with the restart specification at `61b0c39131012c40ff76321bb3650def6e7a9d83`. The original eleven repositories plus the new Board SDK make twelve current organization repositories; no active source is omitted because the historical scope text said eleven.

## Outcome and scope

Decide what each module contributes, where it belongs and what must be repaired, replaced or retired. Preserve independent oracles, source/license provenance, active Pi/P4 paths and external Nostr interoperability. Inventory releases, packages, consumers, tags, issues and links before retiring repository boundaries. This is a decision/research task: no source migration or archival occurs here.

Own this A01 directory and source-disposition decisions; the coordinator alone updates the canonical graph. A02 owns migration rehearsal and archive admission, B01 owns generic SDK API extraction. S01/S02 changes are independently reviewed inputs to future migration, not reasons to copy their old defects.

## Evidence contract

1. Record actual repository commits, clean/dirty state, visibility, archive state, root licenses, tags and releases. Limit imported observations to authorized nonsensitive metadata.
2. Inspect actual source/module consumers and manifests. Query current public registries and bounded code search, recording dates and limits; an empty result does not prove no external use.
3. Classify coherent modules using required behavior and targeted source findings. Name license/notices and an independent behavioral check or explicit retirement rationale. Do not preserve experimental APIs merely because fixtures assert them.
4. Confirm or revise the five release/consumer boundaries with explicit reasons and no generic-SDK dependency on Nostr.
5. Independent review checks the actual input pins, source claims, licensing limits and whether any source/consumer is silently abandoned. Source/release evidence may be stale after another task changes the repository; A02 must reconcile selected current commits again.

No executable product is changed, so prose-presence tests are inappropriate. Validate links, hashes and inventories, review the source-backed decisions, and retain unsolved publication/license questions. No purchase, physical claim or compatibility guarantee is closed.
