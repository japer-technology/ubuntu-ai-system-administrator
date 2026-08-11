# Alternatives to Ubuntu Zombie

This catalogue groups the projects in the same neighbourhood as Ubuntu
Zombie by how closely they overlap with its shape
(`Ubuntu LTS + root user + private interface + LLM`). See
[`ALTERNATIVES-LESSONS.md`](ALTERNATIVES-LESSONS.md) for the rationale
behind the grouping and the concrete lessons drawn from each project.

## Closest direct analogs

Single-host, root or root-capable, audited, approval-gated, intended to
actually *operate* the machine rather than just chat about it.

| Project                               | Why it’s relevant                                                                                                                                                                                                                                                                                                                          |
| ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Missy**                             | Security-first, self-hosted AI assistant for Linux. Default-deny network/filesystem/shell, multi-layer policy engine, Ed25519-signed JSONL audit log, interactive approval TUI, encrypted vault, prompt-injection sanitizer, and code-evolution with git rollback. Probably the closest single-host analog to Ubuntu Zombie. ([GitHub][1]) |
| **LinuxAgent**                        | LLM-driven Linux ops CLI with mandatory human approval, policy engine, SSH guards, runbooks, and audit trails. Very close conceptually. ([GitHub][2])                                                                                                                                                                                      |
| **SysKnife**                          | Plain-language Linux sysadmin agent: proposes typed actions, requires approval, executes via daemon, includes tamper-evident audit chain. Fedora now, Ubuntu planned. ([GitHub][3])                                                                                                                                                        |
| **RHEL Lightspeed / sysadmin-agents** | Multi-agent Linux/RHEL troubleshooting system using Google ADK and linux-mcp-server; more diagnostic/SRE than “own the desktop”. ([GitHub][4])                                                                                                                                                                                             |
| **LinuxOS-AI**                        | “AI-native Linux OS” direction; natural-language system administration, package management, security, diagnosis, optimisation. ([GitHub][5])                                                                                                                                                                                               |

## Strong general-purpose comparables

Not Linux-sysadmin-specific, but local, agentic, and approval-aware;
the ergonomics they have settled on are directly applicable.

| Project                               | Why it’s relevant                                                                                                                                                                                                                                                                                                          |
| ------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Open Interpreter**                  | Lets an LLM run Python/JavaScript/shell locally on your machine through a chat REPL, with mandatory per-action approval before code executes. Local-model support via Ollama and llama.cpp. Closest "general PC operator" comparable. ([GitHub][6])                                                                        |
| **Goose** (AAIF, ex-Block)            | General-purpose AI agent that runs on your machine as a desktop app or CLI, with 70+ MCP extensions for shell, files, browsing, and dev workflows. Multi-provider, local-model friendly, now governed at the Linux Foundation. ([GitHub][7])                                                                               |
| **Cline**                             | Open-source coding agent with CLI, JetBrains, and VS Code front-ends. Edits files, runs shell commands, and browses the web; every edit and command requires human approval unless auto-approve is enabled. SDK plugin system for logging, auditing, and policy enforcement. ([GitHub][8])                                 |
| **Butterfish**                        | AI-augmented shell (`butterfish shell`) for bash/zsh on Linux and macOS with an explicit "agent" mode (`!Run …`) and one-shot command mode (`@…`). Transparent, user-editable prompts and verbose logging instead of hidden behavior. ([GitHub][9])                                                                        |

## Useful building blocks (not products)

Pieces Ubuntu Zombie could *use* or imitate, rather than projects it
competes with.

| Project                               | Why it’s relevant                                                                                                                                                                                                       |
| ------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **linux-administration-mcp**          | MCP server that gives AI assistants SSH-based Linux admin tools (execute, diagnose, services, logs, network, packages, security audit) with hostname-scoped, daily-rotated audit logs for every command. ([GitHub][10]) |
| **HumanLayer**                        | API/SDK for adding human-in-the-loop approval, audit, and high-risk action gating to any LLM agent or framework. Useful as a building block for a Zombie-style approval surface. ([humanlayer.dev][11])                 |
| **Phantasm**                          | Open-source toolkit for building HITL workflows around AI agents: approval layers, web dashboards, audit trails, framework-agnostic. ([GitHub][12])                                                                     |
| **RoboShellGuard**                    | Not a sysadmin agent itself, but a close safety layer: AI risk scoring, approval workflow, SSH command control, audit trail. ([GitHub][13])                                                                             |
| **ShellGuard**                        | MCP server giving LLM agents controlled/read-only SSH access for diagnostics, logs, audits, and troubleshooting. ([Go.dev][14])                                                                                         |

## Adjacent but materially different

These show up in the same searches but optimise for different goals
(developer-in-a-terminal workflow, or broader personal-assistant
platforms). Worth knowing about; not the shape Ubuntu Zombie should
drift into.

| Project                               | Why it’s relevant                                                                                                                                                                                                                                                                    |
| ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Aider**                             | Terminal-based AI pair programmer that edits files and can run shell commands and tests on your local repo, with diff review and undo. Less sysadmin-focused, but a well-known local agentic CLI with explicit-action ergonomics. ([GitHub][15])                                     |
| **ShellGPT (`sgpt`)**                 | CLI wrapper that turns natural language into shell commands and optionally executes them after `[E]xecute / [D]escribe / [A]bort` confirmation. Pluggable backends including local Ollama/LM Studio. The minimal "ask the box to do a thing" pattern. ([GitHub][16])                 |
| **Terminal Agent**                    | Open-source DevOps terminal assistant for diagnostics, command translation, software installation, and environment deployment. ([sagesai.github.io][17])                                                                                                                             |
| **DuckClaw**                          | Local-first open-source personal AI assistant with explicit permission tiers, action preview, audit logs, and sandboxed skills. Broader than sysadmin but philosophically close. ([duckclawlabs.com][18])                                                                            |
| **OpenClaw**                          | Self-hosted agentic system that can run scripts, manage files, call APIs, and operate through local gateway tooling; broader operator platform. ([TechRadar][19])                                                                                                                    |

Best direct comparables to **Ubuntu Zombie**: **Missy**, **LinuxAgent**, **SysKnife**, **LinuxOS-AI**, and **RHEL sysadmin-agents** (single-host, root-capable, audited, approval-gated). **Open Interpreter**, **Goose**, **Cline**, and **Butterfish** are the closest general-purpose local-agent comparables; **linux-administration-mcp**, **HumanLayer**, and **Phantasm** are reusable building blocks rather than full products.

[1]: https://github.com/MissyLabs/missy "GitHub - MissyLabs/missy: Security-first, self-hosted AI assistant for Linux"
[2]: https://github.com/Eilen6316/LinuxAgent "GitHub - Eilen6316/LinuxAgent: LLM-driven Linux operations assistant CLI with mandatory HITL safety, policy engine, runbooks, SSH guards, and audit trails. · GitHub"
[3]: https://github.com/lacs-foundation/sysknife?utm_source=chatgpt.com "GitHub - lacs-foundation/sysknife: AI-managed Linux sysadmin. Plan in ..."
[4]: https://github.com/rhel-lightspeed/sysadmin-agents "GitHub - rhel-lightspeed/sysadmin-agents · GitHub"
[5]: https://github.com/ANVEAI/linuxos-ai "GitHub - ANVEAI/linuxos-ai: The First Step Towards AI-Native Linux OS - Natural language system administration with Gemini AI · GitHub"
[6]: https://github.com/OpenInterpreter/open-interpreter "GitHub - OpenInterpreter/open-interpreter: A natural language interface for computers"
[7]: https://github.com/aaif-goose/goose "GitHub - aaif-goose/goose (formerly block/goose): a general-purpose AI agent that runs on your machine"
[8]: https://github.com/cline/cline "GitHub - cline/cline: The open source coding agent in your IDE and terminal"
[9]: https://github.com/bakks/butterfish "GitHub - bakks/butterfish: A shell with AI superpowers"
[10]: https://github.com/Cosmicjedi/linux-administration-mcp "GitHub - Cosmicjedi/linux-administration-mcp: SSH-based Linux server management MCP server with audit trails"
[11]: https://www.humanlayer.dev/ "HumanLayer — Human-in-the-loop API for AI agents"
[12]: https://github.com/edwinkys/phantasm "GitHub - edwinkys/phantasm: Toolkits to create a human-in-the-loop workflow for AI agents"
[13]: https://github.com/robokeys/roboshellguard?utm_source=chatgpt.com "RoboShellGuard: AI-Assisted Command Approval System - GitHub"
[14]: https://pkg.go.dev/github.com/fawdyinc/shellguard?utm_source=chatgpt.com "shellguard package - github.com/fawdyinc/shellguard - Go Packages"
[15]: https://github.com/Aider-AI/aider "GitHub - Aider-AI/aider: AI pair programming in your terminal"
[16]: https://github.com/TheR1D/shell_gpt "GitHub - TheR1D/shell_gpt: A command-line productivity tool powered by AI large language models"
[17]: https://sagesai.github.io/en/?utm_source=chatgpt.com "Terminal Agent - DevOps Intelligent Assistant"
[18]: https://duckclawlabs.com/ "DuckClaw — Powerful AI, Built Securely"
[19]: https://www.techradar.com/pro/what-is-openclaw?utm_source=chatgpt.com "What is OpenClaw? Agentic AI that can automate any task"
