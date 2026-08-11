#!/usr/bin/env node
// tests/fixtures/stub-pi-mono.mjs
//
// Minimal pi-mono bridge stub used by tests/smoke.sh. Speaks the
// same line-delimited JSON protocol as payload/agent/pi-mono-bridge.mjs
// but does not require `pi` or `node`-native modules other than what
// ships with Node >=18.
//
// The stub script reads ZOMBIE_STUB_PLAN (a JSON array) and emits
// each step in order. Defaults to live progress/token hints, a single
// read-only fs.read call against /etc/os-release, and a "final"
// message — enough to exercise streaming, schema-validation,
// dispatch, and observation paths.

import { createInterface } from "node:readline";
import { writeFileSync } from "node:fs";

function send(obj) { process.stdout.write(JSON.stringify(obj) + "\n"); }

const PROVIDER_KEYS = [
  "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "XAI_API_KEY",
  "OPENROUTER_API_KEY", "MISTRAL_API_KEY", "GROQ_API_KEY",
];

// When ZOMBIE_STUB_START_OUT is set, record the received `start` frame
// and a snapshot of which provider keys are visible in our env. The
// smoke test reads this to assert that pi_mono.run_turn passed the
// resolved provider/model and forwarded only the active provider's
// key (stripping the others).
function recordStart(start) {
  const out = process.env.ZOMBIE_STUB_START_OUT;
  if (!out) return;
  const env = {};
  for (const k of PROVIDER_KEYS) env[k] = k in process.env;
  try {
    writeFileSync(out, JSON.stringify({ start, env }));
  } catch (_e) { /* best-effort */ }
}

const plan = JSON.parse(process.env.ZOMBIE_STUB_PLAN || JSON.stringify([
  { type: "progress", kind: "tool_start", id: "stub-progress", name: "read" },
  { type: "token", delta: "stubbed " },
  { type: "progress", kind: "tool_end", id: "stub-progress", name: "read" },
  { type: "token", delta: "pi-mono " },
  { type: "tool_call", id: "1", name: "fs.read",
    args: { path: "/etc/os-release", max_bytes: 256 } },
  { type: "final", text: "stubbed pi-mono turn complete" },
]));

const rl = createInterface({ input: process.stdin });
let received = 0;

rl.on("line", (line) => {
  received += 1;
  if (received === 1) {
    // First line is always the 'start' frame. Record it, then replay
    // the plan.
    try { recordStart(JSON.parse(line)); } catch (_e) { /* ignore */ }
    let i = 0;
    function step() {
      while (i < plan.length) {
        const item = plan[i++];
        send(item);
        if (item.type === "final" || item.type === "error") {
          process.exit(0);
        }
        // Progress/token frames do not require a Python response, so
        // emit them immediately. Tool calls must pause until the next
        // readline, which is the tool_result from pi_mono.py.
        if (item.type === "tool_call") return;
      }
    }
    step();
    rl.on("line", () => step());
  }
});

rl.on("close", () => process.exit(0));
