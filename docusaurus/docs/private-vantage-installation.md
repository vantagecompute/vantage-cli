---
title: Private Vantage Installation
description: Configure the Vantage CLI to work with 3rd Party/Partner Vantage Installations
---

## 1. Install the Vantage CLI

Install `vantage-cli` with `uv`:

```bash
uv venv
source .venv/bin/activate

uv pip install vantage-cli
```

## 2. Connect to a private Vantage deployment
The `vantage-cli` comes preconfigured to work with [https://vantagecompute.ai](https://vantagecompute.ai) by default.

If you are connecting to a privately hosted Vantage instance you will need to set up your profile accordingly.

Create a profile:

```bash
vantage profile create vantage-example-com \
    --oidc-url=https://auth.example.vantagecompute.ai \
    --api-url=https://apis.example.vantagecompute.ai \
    --tunnel-url=https://tunnel.example.vantagecompute.ai \
     --activate
```

```bash
╭───────────────────────────── Profile Created ───────────────────────────╮
│ ✅ Profile 'vantage-example-com' created successfully!                  │
│ 🎯 Set as active profile!                                               │
╰─────────────────────────────────────────────────────────────────────────╯

                   Profile Details: vantage-example-com                   
┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Property           ┃ Value                                              ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Profile Name       │ vantage-example-com                                │
│ API Base URL       │ https://apis.example.vantagecompute.ai             │
│ OIDC Base URL      │ https://auth.example.vantagecompute.ai             │
│ Tunnel Base URL    │ https://tunnel.example.vantagecompute.ai           │
│ OIDC Domain        │ auth.example.vantagecompute.ai/auth/realms         │
│ OIDC Client ID     │ default                                            │
│ OIDC Max Poll Time │ 300 seconds                                        │
│ Supported Clouds   │ maas, localhost, aws, gcp, azure, on-premises, k8s │
└────────────────────┴────────────────────────────────────────────────────┘
```

## 3. Inspect Identity

```bash
vantage whoami
```

```bash
                Current User Information                
┏━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Property      ┃ Value                                ┃
┡━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Email         │ james@vantagecompute.ai              │
│ Client ID     │ default                              │
│ Profile       │ vantage-example-com                  │
│ Name          │ James Beedy                          │
│ User ID       │ 028da929-d0cf-4984-8bbe-9bc83f49f797 │
│ Token Issued  │ 2025-09-12T22:25:06                  │
│ Token Expires │ 2025-09-12T23:25:06 (✅ Valid)       │
│ Status        │ ✅ Logged in                         │
└───────────────┴──────────────────────────────────────┘
```

```bash
vantage whoami --json | jq '{email: .email, client_id: .client_id}'
```

```bash
{
  "email": "james@vantagecompute.ai",
  "client_id": "default"
}
```

---
See also: [Commands](/cli/commands) | [Troubleshooting](/cli/troubleshooting)
