#!/usr/bin/env node
// tests/fixtures/fake-pi-json.mjs
//
// A stand-in for the real `pi` CLI's `--mode json` output, used to
// exercise payload/agent/pi-mono-bridge.mjs end-to-end without needing
// `@earendil-works/pi-coding-agent` (or a live LLM) on the test host.
//
// It ignores its CLI arguments and emits a realistic AgentSession event
// stream on stdout — the same schema the real `pi --mode json` emits
// (session / agent_start / turn_start / message_* / tool_execution_* /
// turn_end / agent_end) — then exits 0.
//
// ZOMBIE_FAKE_PI_MODE selects the scenario:
//   "text"  (default) — a normal streamed assistant answer.
//   "error"           — a provider/connection error with no answer.
//   "echo"            — answer with the exact -p prompt received, so a
//                       test can assert the bridge forwarded history.
//   "shell-status"    — expected non-zero shell status plus a genuine
//                       tool failure, for progress classification tests.
//   "silent"          — a tool runs but the model never says anything,
//                       so the turn ends with no assistant text.
//   "partial-error"   — some assistant text, then a provider error.
//   "terminal-answer" — a post-tool answer appears only on agent_end.
//   "turn-answer"     — a post-tool answer appears only on turn_end.
//
// Crucially, it does NOT read stdin: the real `pi --mode json` is a
// one-shot event stream, and the bridge must let it exit on stdin EOF
// rather than keeping the pipe open (the 120s-timeout regression).

function out(o) { process.stdout.write(JSON.stringify(o) + "\n"); }

const ANSWER = "Hello from the local model!";
const mode = process.env.ZOMBIE_FAKE_PI_MODE || "text";

// In "echo" mode the fake pi answers with the exact prompt it received
// via -p. The bridge renders the prior conversation into that prompt,
// so smoke.sh can assert cross-turn memory is actually forwarded.
function promptArg() {
  const argv = process.argv.slice(2);
  const i = argv.indexOf("-p");
  if (i !== -1 && i + 1 < argv.length) return argv[i + 1];
  const j = argv.indexOf("--prompt");
  if (j !== -1 && j + 1 < argv.length) return argv[j + 1];
  return "";
}

const base = {
  api: "openai-completions",
  provider: "lmstudio",
  model: "local-model",
  usage: {},
};

out({ type: "session", version: 3, id: "fake", timestamp: new Date().toISOString(), cwd: process.cwd() });
out({ type: "agent_start" });
out({ type: "turn_start" });
out({ type: "message_start", message: { role: "user", content: [{ type: "text", text: "say hi" }], timestamp: Date.now() } });
out({ type: "message_end", message: { role: "user", content: [{ type: "text", text: "say hi" }], timestamp: Date.now() } });

function waitForStdinEof() {
  return new Promise((resolve) => {
    process.stdin.on("end", resolve);
    process.stdin.resume();
  });
}

if (mode === "error") {
  const err = { role: "assistant", content: [], ...base, stopReason: "error", errorMessage: "Connection error.", timestamp: Date.now() };
  out({ type: "message_start", message: err });
  out({ type: "message_end", message: err });
  out({ type: "turn_end", message: err, toolResults: [] });
  out({ type: "agent_end", messages: [err], willRetry: false });
  await waitForStdinEof();
  process.exit(0);
}

const asst = (text) => ({ role: "assistant", content: text ? [{ type: "text", text }] : [], ...base, stopReason: "stop", timestamp: Date.now() });

if (mode === "silent") {
  // The model calls a tool and then stops without producing any text —
  // the "tools ran, then no reply" case.
  const quiet = asst("");
  out({ type: "message_start", message: quiet });
  out({ type: "tool_execution_start", toolCallId: "s1", toolName: "read", args: { path: "/etc/os-release" } });
  out({ type: "tool_execution_end", toolCallId: "s1", toolName: "read", result: "NAME=Ubuntu", isError: false });
  out({ type: "message_end", message: quiet });
  out({ type: "turn_end", message: quiet, toolResults: [] });
  out({ type: "agent_end", messages: [quiet], willRetry: false });
  await waitForStdinEof();
  process.exit(0);
}

if (mode === "terminal-answer") {
  const quiet = asst("");
  const answer = asst("The system is Ubuntu.");
  out({ type: "message_start", message: quiet });
  out({ type: "tool_execution_start", toolCallId: "t1", toolName: "read", args: { path: "/etc/os-release" } });
  out({ type: "tool_execution_end", toolCallId: "t1", toolName: "read", result: "NAME=Ubuntu", isError: false });
  out({ type: "message_end", message: quiet });
  out({ type: "turn_end", message: quiet, toolResults: [] });
  out({ type: "agent_end", messages: [quiet, answer], willRetry: false });
  await waitForStdinEof();
  process.exit(0);
}

if (mode === "turn-answer") {
  const quiet = asst("");
  const answer = asst("The system is Ubuntu.");
  out({ type: "message_start", message: quiet });
  out({ type: "tool_execution_start", toolCallId: "t1", toolName: "read", args: { path: "/etc/os-release" } });
  out({ type: "tool_execution_end", toolCallId: "t1", toolName: "read", result: "NAME=Ubuntu", isError: false });
  out({ type: "message_end", message: quiet });
  out({ type: "turn_end", message: answer, toolResults: [] });
  out({ type: "agent_end", messages: [], willRetry: false });
  await waitForStdinEof();
  process.exit(0);
}

if (mode === "partial-error") {
  // A preamble is streamed, then the provider fails: the error must not
  // be masked by the stale partial text.
  const preamble = asst("Let me check that for you.");
  out({ type: "message_start", message: asst("") });
  out({ type: "message_update", message: preamble, assistantMessageEvent: { type: "text_delta", contentIndex: 0, delta: "Let me check that for you.", partial: preamble } });
  out({ type: "message_end", message: preamble });
  const err = { role: "assistant", content: [], ...base, stopReason: "error", errorMessage: "Connection error.", timestamp: Date.now() };
  out({ type: "message_start", message: err });
  out({ type: "message_end", message: err });
  out({ type: "turn_end", message: err, toolResults: [] });
  out({ type: "agent_end", messages: [err], willRetry: false });
  await waitForStdinEof();
  process.exit(0);
}


if (mode === "echo") {
  const answer = promptArg();
  out({ type: "message_start", message: asst("") });
  out({ type: "message_end", message: asst(answer) });
  out({ type: "turn_end", message: asst(answer), toolResults: [] });
  out({ type: "agent_end", messages: [asst(answer)], willRetry: false });
  await waitForStdinEof();
  process.exit(0);
}

out({ type: "message_start", message: asst("") });
if (mode === "shell-status") {
  out({ type: "tool_execution_start", toolCallId: "probe", toolName: "bash", args: { command: "grep -q missing file" } });
  out({
    type: "tool_execution_end",
    toolCallId: "probe",
    toolName: "bash",
    result: { content: [{ type: "text", text: "Command exited with code 1" }], details: { exitCode: 1 } },
    isError: true,
  });
  out({ type: "tool_execution_start", toolCallId: "broken", toolName: "bash", args: { command: "irrelevant" } });
  out({
    type: "tool_execution_end",
    toolCallId: "broken",
    toolName: "bash",
    result: { content: [{ type: "text", text: "Unable to start shell" }] },
    isError: true,
  });
}
// A tool_execution pair the bridge must tolerate (log only) without
// re-dispatching it as a mediated tool_call.
out({ type: "tool_execution_start", toolCallId: "t1", toolName: "read", args: { path: "/etc/os-release" } });
out({ type: "tool_execution_end", toolCallId: "t1", toolName: "read", result: "NAME=Ubuntu", isError: false });
let acc = "";
for (const piece of ["Hello", " from", " the", " local", " model!"]) {
  acc += piece;
  out({ type: "message_update", message: asst(acc), assistantMessageEvent: { type: "text_delta", contentIndex: 0, delta: piece, partial: asst(acc) } });
}
out({ type: "message_end", message: asst(ANSWER) });
out({ type: "turn_end", message: asst(ANSWER), toolResults: [] });
out({ type: "agent_end", messages: [asst(ANSWER)], willRetry: false });
await waitForStdinEof();
process.exit(0)
