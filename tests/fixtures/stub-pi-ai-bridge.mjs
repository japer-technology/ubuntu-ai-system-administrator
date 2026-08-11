#!/usr/bin/env node
// stub-pi-ai-bridge.mjs — a hermetic stand-in for pi-ai-bridge.mjs used
// by tests/smoke.sh so the model-catalogue path (providers.list_models /
// set_active_model and the /api/models endpoint) can be exercised
// without npm-installing @earendil-works/pi-ai on the test host.
//
// It honours the same wire format as the real bridge: a "list_models"
// op returns a fixed catalogue per provider; any other op returns a
// canned completion. lmstudio returns an empty catalogue to mirror the
// real package (a free-form, local provider).
import { readFileSync } from "node:fs";

const CATALOGUE = {
  openai: [
    { id: "gpt-4o-mini", name: "GPT-4o mini", reasoning: false, contextWindow: 128000 },
    { id: "gpt-4o", name: "GPT-4o", reasoning: false, contextWindow: 128000 },
    { id: "o3-mini", name: "o3-mini", reasoning: true, contextWindow: 200000 },
  ],
  google: [
    { id: "gemini-2.0-flash", name: "Gemini 2.0 Flash", reasoning: false, contextWindow: 1048576 },
  ],
  lmstudio: [],
};

function emit(obj) {
  process.stdout.write(JSON.stringify(obj) + "\n");
}

const raw = process.argv[2]
  ? readFileSync(process.argv[2], "utf8")
  : readFileSync(0, "utf8");
const req = JSON.parse(raw);
const provider = String(req.provider || "").toLowerCase();
// The stub keys its catalogue by the operator-visible provider name as
// the real bridge receives it; gemini is exercised via the "google"
// pi id only inside pi-mono, not here.
const known = CATALOGUE[provider] ?? CATALOGUE.google;

if (String(req.op || "complete").toLowerCase() === "list_models") {
  emit({ ok: true, models: known });
} else {
  emit({ ok: true, text: "stub reply" });
}
