# Example requests for Ubuntu Zombie

Use these prompts as starting points. Ubuntu Zombie is best when you ask
for an outcome, let it inspect first, and approve any change only after it
explains the plan. Read-only requests can run immediately; package,
service, configuration, and destructive changes should trigger the local
policy gate and appear in the audit log.

## Start with situational awareness

- Give me a concise health report for this machine.
- Explain what kind of Ubuntu system this is and what role it seems to
  be serving.
- What changed recently that could explain today's behaviour?
- Summarise CPU, memory, disk, network, and service health in plain
  English.
- Find the top three risks I should fix before relying on this machine.
- Show me what is listening on the network and whether anything looks
  surprising.
- Which users can administer this system, and when did they last log in?
- Tell me whether the zombie itself is healthy, authenticated, and inside
  its Time to Live.

## Diagnose failures

- Explain why the last boot was slow.
- Find failed systemd units and tell me which one matters most.
- Inspect the logs around the last time networking dropped.
- Work out why apt is stuck, locked, or failing.
- Check whether the disk is full because of logs, caches, snapshots, or
  user files.
- Diagnose why DNS lookups are failing, but do not change anything yet.
- Explain why this laptop is running hot or draining battery quickly.
- Investigate intermittent freezes and give me the evidence trail.
- Look for signs that the chat service was restarted or killed.
- Compare the current state with a normal Ubuntu Desktop LTS baseline.

## Make safe maintenance plans

- Check for available updates and tell me what you would install.
- Review held packages and explain whether each hold still makes sense.
- Find old kernels, package caches, and journal files that are safe to
  clean.
- Propose a low-risk cleanup plan that recovers disk space without
  touching personal files.
- Check whether a reboot is needed and why.
- Audit enabled services and recommend anything that should be disabled.
- Review startup applications and explain what is slowing login.
- Check backups or backup tooling and tell me what evidence you find.
- Inspect unattended-upgrades and recommend a safer configuration.
- Create a maintenance checklist I can approve step by step.

## Ask for approved changes

- Install the security updates you just recommended, then show me the
  audit trail.
- Restart only the failed service after explaining the impact.
- Disable a service if it is unnecessary, reversible, and safe to stop.
- Clean package caches and old journals using the safest available
  method.
- Repair broken apt dependencies, but pause for approval before making
  changes.
- Apply the smallest configuration change that fixes the problem, then
  show me the diff.
- Roll back the last change you made if the verification step failed.
- Re-run the verification command and explain every remaining warning.

## Operate Ubuntu Zombie itself

- Show my current provider, model, and whether the active key is present
  without revealing the key.
- List available models and recommend one for careful system
  administration.
- Switch to a cheaper model for routine checks, if one is configured.
- Explain what `/ttl`, `/audit`, `/status`, `/tools`, and `/model` do.
- Show recent audit entries and group them by read-only, approved, and
  denied actions.
- Check whether the policy file matches the documented defaults.
- Tell me which tools are available to you and which ones require
  approval.
- Summarise this conversation so I can load it again later.

## Improve security posture

- Look for obvious hardening gaps without changing the machine.
- Check whether any local services are exposed beyond loopback.
- Review sudoers entries and explain what each privileged path allows.
- Check for world-writable directories in sensitive locations.
- Inspect recent authentication failures and successful administrator
  logins.
- Find stale system users, but do not delete or lock anything yet.
- Review firewall status and recommend a minimal rule set.
- Check whether secrets appear in shell history, logs, or common config
  files, and redact anything you quote.
- Explain the security impact before asking me to approve any fix.

## Prepare for real work

- Before I install developer tools, tell me what is already present.
- Set up the missing package you recommend for this task, with approval.
- Diagnose why my printer, Bluetooth, audio, or display is not working.
- Check whether this machine can safely run a local LLM.
- Find large project folders and tell me which ones are safe candidates
  for archiving.
- Inspect a failing command I paste here and explain the likely root
  cause.
- Turn this messy terminal error into a step-by-step recovery plan.
- Watch for the next failure in the logs and tell me when it happens.

## Good prompt patterns

- "Inspect first. Do not change anything until you have explained the
  evidence and proposed a plan."
- "Make the smallest reversible change, verify it, and show me what you
  changed."
- "If this requires `sudo`, tell me why and wait for approval."
- "Prefer built-in Ubuntu tools and avoid adding new dependencies unless
  they are necessary."
- "Quote commands and file paths, but never reveal secrets."
- "If you are uncertain, stop and ask me instead of guessing."

