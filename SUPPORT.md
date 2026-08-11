# Support

Where to go when something is wrong, or you have a question.

## Quick triage

Before opening anything, run:

```bash
sudo ./scripts/install.sh doctor          # explain what is wrong
/opt/ai-zombie/bin/health-check           # runtime health
sudo /opt/ai-zombie/bin/collect-diagnostics # bundle logs (writes /tmp)
```

Many issues are answered directly in:

- [`docs/QUICKSTART.md`](docs/QUICKSTART.md)
- [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md)
- [`docs/FAQ.md`](docs/FAQ.md)
- [`docs/CONFIGURATION.md`](docs/CONFIGURATION.md)

## I have a question

Open a **GitHub Discussion**:
<https://github.com/japer-technology/ubuntu-zombie/discussions>

Discussions are the right place for:

- "How do I configure …?"
- "Will this work with …?"
- "Show me how to write a custom skill."
- Anything that is not a bug or a feature request.

## I found a bug

Open a **GitHub Issue** using the
[Bug report template](https://github.com/japer-technology/ubuntu-zombie/issues/new?template=bug_report.yml).

Include:

1. Output of `cat /etc/os-release | head -3` (or `lsb_release -a`).
2. Output of `sudo ./scripts/install.sh doctor`.
3. The bundle written by `sudo /opt/ai-zombie/bin/collect-diagnostics`
   (sanitised — see the script for the redaction list).
4. The exact command you ran and what you expected to happen.

## I want a new feature

Open a **GitHub Issue** using the
[Feature request template](https://github.com/japer-technology/ubuntu-zombie/issues/new?template=feature_request.yml).
Explain the use case before the implementation.

## I want to report a security vulnerability

**Do not open a public issue.** Follow the disclosure process in
[`SECURITY.md`](SECURITY.md).

## Response expectations

Ubuntu Zombie is maintained on a best-effort basis. We aim to:

- Triage new issues within **one week**.
- Acknowledge security reports within **48 hours**.
- Cut a patch release for security-impacting bugs within **two
  weeks** of confirmation.

No SLA is offered for non-security issues.

## Commercial support

There is no commercial support offering at this time. If you need
one, open a discussion describing the use case.
