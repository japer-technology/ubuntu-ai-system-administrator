#!/usr/bin/env node
// pi-ai-bridge.mjs — minimal stdin/stdout bridge from Ubuntu Zombie's
// Python chat service to the @earendil-works/pi-ai library.
//
// The Python surface (provider.chat) shells out to this script so
// payload/agent/providers.py can avoid maintaining a second LLM
// client implementation.
//
// Wire format
// -----------
// stdin: a single JSON object. Two operations are supported, selected
// by the optional "op" field (defaults to "complete"):
//
//   complete — run a one-shot chat completion (the default):
//   {
//     "op":       "complete",   // optional
//     "provider": "openai" | "anthropic" | "gemini" | "xai"
//                 | "openrouter" | "mistral" | "groq" | "lmstudio",
//     "model":    "<provider model id>",
//     "messages": [{ "role": "system"|"user"|"assistant",
//                    "content": "..." }, ...]
//   }
//
//   list_models — list the models a provider exposes. Needs no model.
//   For hosted providers the catalogue is pi-ai's static one (no API
//   key required). For a local, OpenAI-compatible provider (lmstudio)
//   the catalogue is fetched live from the server's /models endpoint —
//   its base URL is read from ~/.pi/agent/models.json — so the operator
//   sees the models their server actually serves:
//   {
//     "op":       "list_models",
//     "provider": "openai" | ...
//   }
//
// stdout: a single JSON object
//   { "ok": true,  "text": "<assistant reply>" }                (complete)
//   { "ok": true,  "models": [{ "id", "name", "reasoning",
//                               "contextWindow" }, ...] }        (list_models)
//   { "ok": false, "error": "<message>", "code": "<short id>" } (failure)
//
// The bridge never reads provider keys directly — it relies on the
// environment variables already in scope (OPENAI_API_KEY,
// ANTHROPIC_API_KEY, GEMINI_API_KEY, XAI_API_KEY,
// OPENROUTER_API_KEY, MISTRAL_API_KEY, GROQ_API_KEY,
// LMSTUDIO_API_KEY) which
// payload/agent/providers.py forwards from the secrets file.

import { readFileSync } from "node:fs";
import { delimiter, dirname, join, resolve } from "node:path";
import { execPath } from "node:process";
import { pathToFileURL } from "node:url";

// Map Ubuntu Zombie provider names (operator-visible) to the provider
// ids that @earendil-works/pi-ai uses internally. Keep this list in
// lockstep with providers.py's _PI_AI_PROVIDERS.
const PROVIDER_MAP = {
  openai: "openai",
  anthropic: "anthropic",
  gemini: "google",
  xai: "xai",
  openrouter: "openrouter",
  mistral: "mistral",
  groq: "groq",
  lmstudio: "lmstudio",
};

// Map provider name to the env var that must be set. Mirrors
// providers.py so error messages on the Python side and here agree.
const KEY_ENV = {
  openai: "OPENAI_API_KEY",
  anthropic: "ANTHROPIC_API_KEY",
  gemini: "GEMINI_API_KEY",
  xai: "XAI_API_KEY",
  openrouter: "OPENROUTER_API_KEY",
  mistral: "MISTRAL_API_KEY",
  groq: "GROQ_API_KEY",
  lmstudio: "LMSTUDIO_API_KEY",
};

function emit(obj) {
  process.stdout.write(JSON.stringify(obj));
  process.stdout.write("\n");
}

function die(error, code = "bridge_error") {
  emit({ ok: false, error: String(error), code });
  process.exit(1);
}

// Resolve the OpenAI-compatible base URL for a local/custom provider.
//
// Providers such as `lmstudio` have no static catalogue in pi-ai; their
// models live on the server itself. scripts/install.sh records the
// server URL in ~/.pi/agent/models.json (the same file pi-mono reads),
// so we look the provider's `baseUrl` up there. The path is overridable
// via ZOMBIE_PI_MODELS_JSON for tests. An explicit OPENAI_BASE_URL /
// OPENAI_API_BASE env wins for the openai provider so an operator
// pointing the hosted client at a local server still gets a live list.
// Returns the trimmed base URL string, or "" when none is configured or
// the configured value is not an absolute http(s) URL.
function localBaseUrl(provider) {
  let baseUrl = "";
  if (provider === "openai") {
    const envUrl = process.env.OPENAI_BASE_URL || process.env.OPENAI_API_BASE;
    if (envUrl) baseUrl = String(envUrl).trim();
  }
  if (!baseUrl) {
    const entry = customProviderEntry(provider);
    const fromCfg = entry && entry.baseUrl;
    baseUrl = typeof fromCfg === "string" ? fromCfg.trim() : "";
  }
  // Only an absolute http(s) URL can be queried; anything else (a
  // relative path, a bare host, an empty string) is unusable here.
  return /^https?:\/\//i.test(baseUrl) ? baseUrl : "";
}

// Read the provider's entry from ~/.pi/agent/models.json (the file
// scripts/install.sh writes for local providers and pi-mono reads).
// Returns the raw object ({ baseUrl, api, compat, ... }) or null when
// the file or entry is missing/unparseable.
function customProviderEntry(provider) {
  const path =
    process.env.ZOMBIE_PI_MODELS_JSON ||
    (process.env.HOME ? join(process.env.HOME, ".pi", "agent", "models.json") : "");
  if (!path) return null;
  let cfg;
  try {
    cfg = JSON.parse(readFileSync(path, "utf8"));
  } catch {
    return null;
  }
  const entry = cfg && cfg.providers && cfg.providers[provider];
  return entry && typeof entry === "object" ? entry : null;
}

// How long to wait for the local server's /models endpoint before giving
// up, so `/model` never blocks on an unreachable or wedged server.
const LOCAL_MODELS_TIMEOUT_MS = 8000;

// Fetch the catalogue a local OpenAI-compatible server advertises via
// GET {baseUrl}/models (the standard /v1/models route — baseUrl already
// includes the /v1 segment). Returns the normalised model list, or
// throws on a network/parse error so the caller can fall back to the
// static catalogue. Bounded by a short timeout so /model never hangs on
// an unreachable server.
async function fetchLiveModels(baseUrl, keyEnv) {
  const url = `${baseUrl.replace(/\/+$/, "")}/models`;
  const headers = { Accept: "application/json" };
  const key = keyEnv && process.env[keyEnv];
  if (key) headers.Authorization = "Bearer " + key;
  const resp = await fetch(url, {
    headers,
    signal: AbortSignal.timeout(LOCAL_MODELS_TIMEOUT_MS),
  });
  if (!resp.ok) {
    throw new Error(`GET ${url} -> HTTP ${resp.status}`);
  }
  const body = await resp.json();
  // OpenAI lists models under `data`; tolerate a bare array too.
  const rows = Array.isArray(body) ? body : Array.isArray(body?.data) ? body.data : [];
  return rows
    .map((m) => (typeof m === "string" ? { id: m } : m))
    .filter((m) => m && m.id)
    .map((m) => ({
      id: String(m.id),
      name: String(m.name || m.id),
      reasoning: !!m.reasoning,
      // `context_length` is the snake_case field local OpenAI-compatible
      // servers (LM Studio, llama.cpp) emit; `contextWindow` mirrors the
      // pi-ai catalogue shape. Honour whichever the server provided.
      contextWindow:
        typeof m.contextWindow === "number"
          ? m.contextWindow
          : typeof m.context_length === "number"
            ? m.context_length
            : null,
    }));
}

// Resolve and import @earendil-works/pi-ai/compat.
//
// The package is installed *globally* (npm install -g, see
// scripts/install.sh) and this bridge is deployed to
// /opt/ai-zombie/agent/, which is outside any node_modules tree. Node's
// ESM loader resolves bare specifiers by walking node_modules up from
// the importing file and — unlike CommonJS require — ignores NODE_PATH,
// so a plain `import("@earendil-works/pi-ai/compat")` cannot see a global
// install and dies with ERR_MODULE_NOT_FOUND. That broke the /model
// command (and every completion) on a normal deployment.
//
// We therefore try the bare import first (covers a local/dev install or
// a bundled node_modules) and, if that fails, locate the package inside
// the known global node_modules directories and import its real entry
// file by absolute URL. Reading the entry from package.json honours
// pi-ai's "exports" map (it exposes only an "import" condition, so
// require.resolve cannot be used here).
let PI_AI_CACHE;

function piAiEntry(packageDir, subpath) {
  let pkg;
  try {
    pkg = JSON.parse(readFileSync(join(packageDir, "package.json"), "utf8"));
  } catch {
    return null;
  }
  let rel;
  const exp = pkg.exports;
  const key = subpath === "." ? "." : `./${subpath}`;
  const entry = typeof exp === "string" && key === "." ? exp : exp?.[key];
  if (typeof entry === "string") {
    rel = entry;
  } else if (entry && typeof entry === "object") {
    rel = entry.import || entry.node || entry.default;
  }
  if (!rel && key === ".") rel = pkg.module || pkg.main || "index.js";
  if (!rel) return null;
  return resolve(packageDir, rel);
}

function globalModuleDirs() {
  const dirs = [];
  const seen = new Set();
  const add = (dir) => {
    if (dir && !seen.has(dir)) {
      seen.add(dir);
      dirs.push(dir);
    }
  };
  // NODE_PATH (forwarded by providers.py) — split on the platform
  // delimiter and honour each entry even though ESM ignores it natively.
  if (process.env.NODE_PATH) {
    for (const part of process.env.NODE_PATH.split(delimiter)) add(part);
  }
  // Standard global prefix for the running node: <prefix>/lib/node_modules
  // (e.g. /usr/bin/node -> /usr/lib/node_modules on the NodeSource build
  // this project installs).
  add(resolve(dirname(execPath), "..", "lib", "node_modules"));
  // Windows-style layout and common Unix fallbacks.
  add(resolve(dirname(execPath), "node_modules"));
  add("/usr/lib/node_modules");
  add("/usr/local/lib/node_modules");
  return dirs;
}

async function loadPiAi() {
  if (PI_AI_CACHE) return PI_AI_CACHE;
  let lastErr;
  try {
    PI_AI_CACHE = await import("@earendil-works/pi-ai/compat");
    return PI_AI_CACHE;
  } catch (err) {
    lastErr = err;
  }
  const searched = [];
  for (const base of globalModuleDirs()) {
    searched.push(base);
    const entry = piAiEntry(join(base, "@earendil-works", "pi-ai"), "compat");
    if (!entry) continue;
    try {
      PI_AI_CACHE = await import(pathToFileURL(entry).href);
      return PI_AI_CACHE;
    } catch (err) {
      lastErr = err;
    }
  }
  const where = searched.length
    ? ` (searched: ${searched.join(", ")})`
    : "";
  die(
    `failed to load @earendil-works/pi-ai: ${lastErr ? lastErr.message : "not found"}${where}. ` +
      "Reinstall via scripts/install.sh.",
    "pi_ai_missing",
  );
}

async function readStdin() {
  // Allow the caller to pass the request as a file path argument
  // (used by unit tests) or, by default, read JSON from stdin.
  if (process.argv[2]) {
    return readFileSync(process.argv[2], "utf8");
  }
  const chunks = [];
  for await (const chunk of process.stdin) chunks.push(chunk);
  return Buffer.concat(chunks).toString("utf8");
}

async function main() {
  let raw;
  try {
    raw = await readStdin();
  } catch (err) {
    die(`failed to read request from stdin: ${err.message}`, "stdin_error");
  }

  let req;
  try {
    req = JSON.parse(raw);
  } catch (err) {
    die(`request is not valid JSON: ${err.message}`, "bad_request");
  }

  const provider = String(req.provider || "").toLowerCase();
  const piProvider = PROVIDER_MAP[provider];
  if (!piProvider) {
    die(
      `unknown provider "${provider}"; supported: ${Object.keys(PROVIDER_MAP).join(", ")}`,
      "unknown_provider",
    );
  }

  // list_models: a local, OpenAI-compatible provider (lmstudio, or any
  // provider pointed at a custom base URL) has no static catalogue in
  // pi-ai, so query the server's live /models endpoint first. Only fall
  // back to pi-ai's bundled catalogue when no live source is configured
  // or the server cannot be reached — this is what restores the model
  // list for the local-LLM deployments that ship by default.
  const op = String(req.op || "complete").toLowerCase();
  if (op === "list_models") {
    const baseUrl = localBaseUrl(provider);
    if (baseUrl) {
      try {
        const live = await fetchLiveModels(baseUrl, KEY_ENV[provider]);
        if (live.length) {
          emit({ ok: true, models: live });
          return;
        }
      } catch (err) {
        // A local provider has no static fallback, so surface why the
        // live query failed instead of silently returning an empty list.
        if (provider === "lmstudio") {
          die(
            `failed to list models from local server at ${baseUrl}: ${err.message}`,
            "list_failed",
          );
        }
        // Hosted provider with a base-URL override: fall through to the
        // bundled catalogue below.
      }
    }
    const pi = await loadPiAi();
    let models;
    try {
      models = pi.getModels(piProvider) || [];
    } catch (err) {
      die(
        `failed to list models for provider "${provider}": ${err.message}`,
        "list_failed",
      );
    }
    const out = models
      .filter((m) => m && m.id)
      .map((m) => ({
        id: String(m.id),
        name: String(m.name || m.id),
        reasoning: !!m.reasoning,
        contextWindow:
          typeof m.contextWindow === "number" ? m.contextWindow : null,
      }));
    emit({ ok: true, models: out });
    return;
  }

  const keyEnv = KEY_ENV[provider];
  if (keyEnv && !process.env[keyEnv]) {
    die(`${keyEnv} is not set`, "missing_key");
  }

  const model = String(req.model || "").trim();
  if (!model) {
    die(`model id is required for provider "${provider}"`, "missing_model");
  }

  const messages = Array.isArray(req.messages) ? req.messages : [];
  // pi-ai's Context separates the system prompt from the message list.
  const systemParts = [];
  const userMessages = [];
  for (const m of messages) {
    if (!m || typeof m !== "object") continue;
    const role = String(m.role || "");
    const content = m.content == null ? "" : String(m.content);
    if (role === "system") {
      systemParts.push(content);
    } else if (role === "user" || role === "assistant") {
      userMessages.push({ role, content });
    }
  }

  const pi = await loadPiAi();

  // pi-ai's getModel() reads only the static *built-in* catalogue; a
  // local, OpenAI-compatible provider (lmstudio — the shipped llama.cpp
  // default) and any model the catalogue has not caught up with resolve
  // to undefined rather than throwing. Passing that undefined handle to
  // complete() used to crash with the cryptic "Cannot read properties
  // of undefined (reading 'api')", so treat both outcomes the same and
  // synthesise a model handle from ~/.pi/agent/models.json instead.
  let modelHandle;
  try {
    modelHandle = pi.getModel(piProvider, model);
  } catch {
    modelHandle = undefined;
  }
  let explicitApiKey;
  if (!modelHandle) {
    const baseUrl = localBaseUrl(provider);
    if (!baseUrl) {
      die(
        `unknown model "${model}" for provider "${provider}": not in the ` +
          "pi-ai catalogue and no local endpoint is configured in " +
          "~/.pi/agent/models.json",
        "unknown_model",
      );
    }
    const entry = customProviderEntry(provider) || {};
    modelHandle = {
      id: model,
      name: model,
      api:
        typeof entry.api === "string" && entry.api
          ? entry.api
          : "openai-completions",
      provider: piProvider,
      baseUrl,
      reasoning: false,
      input: ["text"],
      cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
      contextWindow: 128000,
      maxTokens: 4096,
      ...(entry.compat && typeof entry.compat === "object"
        ? { compat: entry.compat }
        : {}),
    };
    // pi-ai's env key injection only knows built-in providers, so a
    // synthesised model needs the key passed explicitly. Local servers
    // accept any placeholder value.
    explicitApiKey = keyEnv ? process.env[keyEnv] : undefined;
  }

  const context = {
    systemPrompt: systemParts.join("\n\n") || undefined,
    messages: userMessages,
    tools: [],
  };

  let result;
  try {
    result = await pi.complete(
      modelHandle,
      context,
      explicitApiKey ? { apiKey: explicitApiKey } : undefined,
    );
  } catch (err) {
    die(`provider call failed: ${err.message || err}`, "provider_error");
  }
  // pi-ai reports provider-level failures in-band on the assistant
  // message instead of throwing; surface those as errors too so the
  // connectivity probe cannot mistake an errored turn for success.
  if (result && result.stopReason === "error") {
    die(
      `provider call failed: ${result.errorMessage || "unknown provider error"}`,
      "provider_error",
    );
  }

  // pi-ai's complete() returns the assistant message. Concatenate text
  // parts when the provider returns structured content.
  emit({ ok: true, text: extractAssistantText(result) });
}

function extractAssistantText(message) {
  if (!message || message.role !== "assistant") return "";
  const content = message.content;
  if (typeof content === "string") return content;
  if (!Array.isArray(content)) return "";
  return content.map(textOfPart).join("");
}

function textOfPart(part) {
  if (typeof part === "string") return part;
  if (part && typeof part.text === "string") return part.text;
  return "";
}

main().catch((err) => die(err.stack || String(err), "uncaught"));
