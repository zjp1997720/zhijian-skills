# Troubleshooting

## Theme appears only after a delay

Confirm the injector registered `Page.addScriptToEvaluateOnNewDocument`, uses `Page.domContentEventFired`, and the New Task samples retain the active background at 0/50/150/500 ms. Avoid route polling delays and DOM-class debounce timers.

## Home Banner or cards disappear

Codex changed a home selector or container relationship. Run core verification. If `home-enhancement-hook-missing` appears, treat the page as degraded rather than hiding native content. Update stable semantic hooks only after inspecting the live DOM.

## Workspace tabs are invisible but clickable

Check the main header background and the tab title layer. Keep `header.app-header-tint` transparent, preserve pointer events, and avoid absolute overlays above the native tab strip.

## Banner looks half-filled or crops the subject

The image file itself may contain too much empty area or the focal point may sit outside the responsive crop. Inspect the full source, then test 1440, 1920, 2304, and a narrow viewport. Regenerate or edit the asset with the left text-safe zone and right-center subject contract; do not patch crop failures with fixed pixel offsets for one viewport.

## Full-page background hurts readability

Use `artPlacement: hero`, or regenerate the background with lower frequency and a calmer center. Keep content panels opaque enough for body text. Full-page art is a deliberate mode, not a default.

## Selected conversation feels harsh

Use `selected` as a quiet paper tone, keep a small radius, and use a subtle inset edge. Remove `border-left`; do not replace it with a saturated bar.

## Inject or verify cannot reach CDP

Check that Codex was launched through the managed start script and that the saved port is loopback-only. Do not attach to a foreign listener. If Codex was already open normally, obtain restart authorization and use `--restart-existing`.

## Restore stops while Codex is running

The saved CDP endpoint could not be verified. This is a safety stop. Ask for restart authorization, then use `--restart-codex`; do not kill a process based only on a stale PID.

## Codex update changes selectors

Run deterministic tests, doctor, core-only verification, then strict verification. Repair semantic selectors in the injected CSS/renderer and add a fixture for the observed failure. Keep the previous engine snapshot until both home and task pass.
