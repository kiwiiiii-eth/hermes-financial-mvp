# Jetson Install Guide

This guide describes a generic Jetson deployment pattern for a local Hermes installation.

Do not commit machine-specific SSH aliases, IP addresses, usernames, tokens, or private paths to this public repo.

## Target Skill Path

For a user-local Hermes skill:

```text
~/.hermes/skills/custom/crypto-market-anomaly/SKILL.md
```

## Install

From this repo:

```bash
mkdir -p ~/.hermes/skills/custom/crypto-market-anomaly
cp skills/custom/crypto-market-anomaly/SKILL.md ~/.hermes/skills/custom/crypto-market-anomaly/SKILL.md
```

## Verify

```bash
hermes skills list | grep crypto-market-anomaly
```

If `hermes` is not on PATH in a non-interactive SSH session, use the full path to the local Hermes binary.

## Test Load

```bash
hermes --skills crypto-market-anomaly -z "Analyze this sample BTCUSDT anomaly input using MVP v1 format."
```

The current Hermes session may not see newly created skills immediately. Start a new session if needed.
