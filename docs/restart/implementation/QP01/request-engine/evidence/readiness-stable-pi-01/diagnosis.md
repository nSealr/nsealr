The first final Pi attempt on3633e8f0 built the actual source-matched library,
then failed the existing provisioning control:188/189 tests passed, while
`test_actual_driver_orders_full_pi_then_client_with_same_library` correctly
requires exactly build -> entire Pi CI -> one actual-client invocation. Adding
a second Node invocation for readiness controls to `ci()` violated that frozen
sequence. The real client campaign was never reached by this attempt.

Remove only that added driver call. The five separate no-request controls have
their explicit focused command/receipt and remain available through
`client-exchange.ts --readiness-controls`; they are not silently attributed to
the default driver. Keep the original provisioning test, Make recipe, full Pi
suite and default client invocation unchanged. The entire required Pi+client
path must run again because its previous attempt failed and the driver changed.
