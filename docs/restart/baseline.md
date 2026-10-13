# Measured baseline

Audit date: 2026-10-13. These source observations identify the starting point; they are not claims about later candidates.

| Source | Commit | Observation |
| --- | --- | --- |
| `nsealr` (formerly firmware) | `367c9e5254be5468311f704bed84a5bae994bb1e` | Rust core and desktop harness; no completed device app; `signing_disabled` remains intentional |
| `companion` | `13414320537d0208fc3ef8e43bd0723c98c1d5e0` | Host packages and NIP-46 client; no complete hardware-backed signing server |
| `raspberry` | `d1534d9dcfba8fe4a35cea2ed3529e32a5003dc6` | Python signing path and adapters; physical product acceptance absent |
| `specs` | `8bb8cca71355bcf8d81a093bcee9f3fe6915b121` | Useful vectors/contracts mixed with experimental product-policy assumptions |
| hardware phase branch | `cea1c34c9c97e500c763f132a13373b4dca74876` | Five schematic sheets and an empty PCB; not a fabrication-ready design |

The local audit executed the software suites, core target compilation and selected cross-repository integration checks. Baseline integration failures included generated API drift, launcher stderr noise and environment/layout assumptions. Constituent integration checks passed across corrected runs; no uninterrupted all-green full-program CI result is claimed.

Security review identified boundary work for peer/user identity, secret ownership, one-use approval and bounded input handling. Existing tests remain useful but cannot certify these properties merely by passing. Tasks S01–S03 and K01 own correction and regression evidence.

The complete local audit, raw logs, source pins and GitHub preservation inventory are retained in the maintainer's private restart archive. Public claims must be independently reproducible from source and selected evidence before release; this summary does not substitute for those artifacts.
