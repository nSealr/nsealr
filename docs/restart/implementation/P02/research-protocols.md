# Opt-in workflow and developer research scripts

These are manual procedures for the profile owner to execute later. No participant was contacted or observed while preparing P02. Read the [qualification plan](compatibility-plan.md) first. A pilot does not replace its profile's technical security/release gates, and source inspection does not count as an observed session.

## Prepare one bounded session

The relevant owner selects the exact profile/workflow and checks its canonical prerequisites. C01/C02 with D03 or V03/S05 own connected participants; QH01 with Q04 or Q05 owns that optical profile's participants; B03 identifies an independent Board developer. A participant for one delivery is never a resource prerequisite for an unrelated delivery. Physical hardware, operator, instruments, participants and independent developer availability remain unknown until identified.

Use identified authorized test assemblies, controlled fixture accounts/peers/relays and an already reviewed bounded procedure. A pre-production engineering observation is labelled as such. Use synthetic public text and messages. Do not ask anyone to enter an existing identity, personal backup, private conversation, payment or other production secret. A fixture recovery exercise still stays on the device's local recovery path. No script orders hardware, burns fuses, replaces an owner's root or contacts third parties.

Before the session, fill the exact source/build/browser/OS/device/relay/contract record in the qualification plan. Check fixture identities and expected public keys through an independent oracle. Reconcile actual browser binaries, extension/native-host artifacts and lifecycle support; package tests alone are insufficient. Rehearse injected engineering failures with the operator before asking a participant to use the device. Select accessible display/input and stop conditions appropriate to that participant; document assistance.

## Consent and observation opening

A researcher can read this invitation to an already voluntarily enrolled person:

> Vorremmo osservare una prova di questo dispositivo usando solo dati e identità di test. Puoi fermarti o saltare un passaggio in qualsiasi momento. Annoteremo i passaggi, i tempi e le difficoltà senza il tuo nome; non raccoglieremo chiavi o backup reali. Non sono previste registrazioni audio o video. Vuoi partecipare a questa specifica prova?

Continue only after an explicit voluntary answer for this session. Silence is not consent. Do not create a recording or automatic telemetry stream. Explain where private notes stay, what anonymous aggregate may later be shared, and how to ask the researcher to remove the session's notes before aggregation. Do not publish raw participant notes in Git. Collect no name, contact address or personal account. Use a session identifier that is not linked to identity. Recruitment and any follow-up contact are separate opt-in work of the applicable profile owner, not an action executed by this document.

Ask these open questions before giving instructions: what would you expect this device to protect; what would you expect to appear on its display; what would you do if the displayed account or action looked wrong? Record misunderstandings without coaching them away. Explain fixture-only boundaries and the ability to stop; do not describe success as a foregone conclusion.

## Script A — setup and same-identity recovery

1. Hand over the exact candidate's ordinary user instructions and test assembly. State the goal: establish the designated fixture identity, identify its public key and prepare its local recovery method. The researcher observes rather than completing the steps.
2. Start elapsed setup time when the participant starts the instructions. Record prompts, navigation, hesitation and each intervention, with its time. Ask the person to explain the displayed account and what has been authorized. Do not collect recovery text, a screen photograph of it or keystrokes.
3. Have the person compare the device's full public key with the independent fixture expectation. An unexpected identity stops the session and creates an owned finding. A visually plausible fingerprint alone is insufficient.
4. Run the profile's reviewed local fixture recovery procedure on an identified authorized test unit/session. Do not invent a reset or persistent custody promise for a volatile QR profile. The expected key comes from an independently retained fixture, not a restored host descriptor.
5. Observe entry/checksum handling and same-identity confirmation locally. Record elapsed recovery time, mistakes, abandoned steps and help. Record only a pass/fail/inconclusive identity result and public test key, never backup material.
6. Explain and ask the participant to describe what a copied backup means, what a PIN does on this profile, and whether a backup copy revokes another device. Do not infer understanding from a successful click sequence.

Device entropy/import failures, destructive reset and interrupted storage/update tests belong to the separately authorized engineering procedure and their actual target owners. This human script cannot make an unqualified recovery design safe.

## Script B — connected public actions and messages

1. Select one exact client build and browser. Pair through the selected NIP-07 or NIP-46 path using the fixture account. Observe whether the person can distinguish the transport connection from their user identity and from signature permission.
2. Ask for a simple public fixture post, then the other applicable G03 catalog actions. Before each approval, ask what the device will sign and whether every relevant field can be found. Do not read the answer or scroll the device for the person. Preserve the accepted review/input sequence and independently verified public result.
3. Exercise a clearly announced cancellation and an operator-controlled disconnect under the rehearsed procedure. Observe the displayed result and whether the person expects a retry or a new approval. Engineering traces distinguish an abandoned client promise from an implemented cancellation channel. Never let a failed transport silently repeat signing.
4. Change the controlled fixture account or application origin and request a new action. Check independent rebinding and the participant's interpretation of host-supplied names. Do not imply that the device has attested a website identity.
5. Only when the admitted connected DM implementation exists, perform M01–M08: local DM-relay setup/replacement, peer and sender copies of a one-to-one synthetic text message, receive/context explanation and required relay AUTH. The person identifies the recipient/plaintext and the distinct authentication operation. Record actual binding/context evidence; primitive calls are not a verified-message result.
6. Exercise explicit unsupported NIP-04 and a controlled missing/invalid recipient advertisement. The admitted workflow must fail clearly without arbitrary-relay or opaque-signing fallback. A client incompatibility is a finding, not a reason to remove device review.
7. Record review and end-to-end durations separately from relay publication. Stop on unexpected signing/identity, ambiguous secret exposure, a violated consent boundary or unsafe behavior. Save the exact technical failure through the owner; do not keep the person retrying until a green result appears.

A full client×browser×connector matrix is executed by C01/C02. One participant's successful post does not fill unobserved matrix cells or prove safe DM, different browsers, another profile or market demand.

## Script C — offline Pi or P4

1. Identify the actual profile/assembly and its active interfaces, firmware and volatile identity rule. Locally load the fixture identity and verify its public key. Explain the ordinary operation QR and separate local recovery flow without suggesting a pairing QR is a signing transaction.
2. Ask the person to initiate one supported client action, transfer the Bridge request to the signer, inspect the complete action locally, and transfer the public response back. Record scan attempts, conditions, assistance, transfer/review/return durations and independently verified correlation/signature/publication results.
3. Run the rehearsed cancellation, wrong/expired request and harmless duplicate/mixed-frame cases. The participant should see a clear result; the engineering trace must show bounded decoding and no resurrected authorization. A codec round trip or video demonstration alone is not optical qualification.
4. Interrupt power/session using the approved safe test procedure, then observe local reload and same expected identity. The profile must not imply persistent grants or identity storage it has not qualified. Test whether the instructions make this behavior understandable.
5. Present a DM/automation request as an explicitly unsupported fixture. The first Pi/P4 delivery rejects it. Record clarity of that limitation without advertising a universal security rank.

Pi and P4 observations are separate. Do not fill one profile's camera, radio, power-loss, recovery or usability evidence from the other.

## Script D — independent generic Board developer

1. B03 identifies a developer independent of the implementation author and records relevant prior experience and permitted assistance level without personal identity. Supply the proposed release's public Board/SDK/bootloader/toolchain documentation and an identified authorized test assembly. No nsealr checkout or client is supplied or required.
2. Ask for a clean build and physical run of the concrete non-Nostr example, following the ordinary docs. Record source/lock/tool/binary/assembly identities, elapsed time to the first demonstrated result, errors, help and changes. A different AI agent may assist if that matches the declared condition; assisted success cannot be labelled unaided human adoption.
3. Demonstrate the claimed actual input/display/peripheral/security-service behavior. Check finite key-handle/entropy/storage failure cases through the reviewed engineering procedure. A stub or successful availability flag cannot stand in for a missing chip or hardware operation.
4. Ask the developer to explain allowed firmware ownership, retained/erased secrets and irreversible limits. Observe only pre-authorized non-destructive or sacrificial lifecycle procedures. MCU-owner roots and vendor-controlled SE authority remain distinct. A full reset must not be improvised during the observation.
5. Record whether the developer could reproduce the result without private context and identify what would be needed for their own application. Future SSH/FIDO/wallet ideas are learning inputs, not qualified applications or a commitment to hostile-app isolation.
6. B03 separately supplies generic production-test/yield/provisioning/entropy-release-binary evidence. The independent developer observation cannot borrow a Nostr production or Signer pilot result, and those pilots are not its prerequisite.

## Follow-up and interpretation

After the workflow, ask: what action did you believe you authorized; what would you do after loss of power/device/backup; which step would prevent you from using or developing with this again? Record actual explanations and difficulties, not only satisfaction scores. Distinguish technical failure, instruction failure, untested step and withdrawal. Escalate unexpected signing/identity or unsafe lifecycle behavior before another session.

A four-week voluntary use follow-up can be proposed by that profile after its applicable gates. Participation and future contact must be separately chosen; no ongoing telemetry or automatic messages are installed by P02. The dated8/10 setup and7/10 weekly-use figures are hypotheses for learning. Report sample size, withdrawals, assistance, workflow/version changes and missing observations. Do not infer statistical adoption, retention, broad compatibility or future popularity. Existing canonical release criteria still apply; hypothesis labels never waive them.

## Minimal private session record

```text
Session ID (no name/contact):
Profile / workflow / scenario IDs / owner task:
Consent and withdrawal option explained; explicit agreement:
Exact run manifest and technical evidence references:
Declared assistance condition and actual interventions:
Task start/end and setup/recovery/review/transfer/publication durations:
Attempted actions; completed/failed/withdrawn/unobserved steps:
Participant explanation and observed difficulties (no secret material):
Independent identity/signature/correlation result:
Publication result, recorded separately:
Pass/fail/inconclusive at the exact claimed boundary:
Unexpected/unsafe behavior; stopped at:
Owned issue and next experiment:
Private retention/removal choice; allowed anonymous aggregate:
```

Only consented anonymous aggregates and non-sensitive technical findings become public project evidence. Raw notes, recovery material, private conversations, source credentials and copyrighted manuals never become convenient Git artifacts. P02 delivers these procedures; applicable profile owners later supply actual observations and evidence.
