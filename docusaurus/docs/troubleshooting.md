---
title: Troubleshooting
description: Common issues and solutions for Vantage CLI
---

Quick answers for frequent issues.

## Vantage CLI Authentication Fails

```bash
vantage login  # complete device flow in browser
```

If the terminal shows a "loop": verify network access to OIDC URL and that system clock skew < 60s.

## Expired Token

```bash
vantage whoami  # triggers refresh if possible
vantage login   # re-authenticate if still failing
```

## Profile Not Found

```bash
vantage profile list
vantage profile create --name dev --set-active
```

## JSON Output / Parsing Errors

Ensure you used `--json` before piping to `jq`:

```bash
vantage clusters list --json | jq '.clusters | length'
```

## Network / API Errors

- Add `-v` for debug logs
- Confirm configured endpoints

## Token Cache Corruption

Remove token file (path may differ by install) then re-login:

```bash
rm ~/.config/vantage-cli/tokens/<profile>.json 2>/dev/null || true
vantage login
```

## Rate Limits / Throttling

Retry after brief backoff; excessive rapid polling may be limited.

## Still Stuck?

Open an issue including: command run, abbreviated error, Python version, profile name (not tokens).
