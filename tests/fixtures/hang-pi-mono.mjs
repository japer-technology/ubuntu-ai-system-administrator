#!/usr/bin/env node
// tests/fixtures/hang-pi-mono.mjs
//
// A deliberately wedged pi-mono bridge: it reads the `start` frame and
// then never emits an event. Used by tests/smoke.sh to prove that
// pi_mono.run_turn's idle watchdog terminates a hung turn and raises a
// clean BridgeError rather than blocking forever (the "Hello hangs
// forever" regression).

import { createInterface } from "node:readline";

const rl = createInterface({ input: process.stdin });
rl.on("line", () => {
  // Swallow input and hang. Keep the process alive indefinitely (a very
  // long interval ~ 12 days) so the driver-side watchdog is the only
  // thing that can end the turn.
  const HANG_FOREVER_MS = 1 << 30;
  setInterval(() => {}, HANG_FOREVER_MS);
});
