---
layout: page
title: Architecture
nav_order: 40
permalink: /architecture/
description: Internal architecture overview of Vantage CLI
---

Architecture
============

Concise view of internal structure & responsibilities.

Goals
-----

- Separate presentation (CLI/Rich) from logic (auth, config, clients)
- Safe token lifecycle (acquire, cache, refresh)
- Predictable profile-scoped configuration
- Async I/O for network efficiency
- Minimal global state

Module Map
----------

```text
vantage_cli/
    main.py        # Typer app + command registration
    auth.py        # Device code + refresh + persona
    cache.py       # Token cache load/save
    client.py      # Low-level HTTP helpers
    gql_client.py  # Async GraphQL client factory
    config.py      # Settings + profile mgmt + decorator
    constants.py   # Paths, filenames, env var names
    exceptions.py  # Exception hierarchy + Abort helper
    format.py      # Rich / JSON output helpers
    schemas.py     # Pydantic models (TokenSet, Persona, Settings, Persona)
    time_loop.py   # Simple polling / timing utility
```

Execution Flow
--------------

1. CLI invoked
2. Active profile resolved
3. Settings loaded (file + env)
4. Tokens loaded / refreshed
5. Command executes (GraphQL/HTTP as needed)
6. Output rendered (human or JSON)

Authentication Lifecycle
------------------------

High-level states for token acquisition, caching, usage, and refresh.

```mermaid
flowchart LR
    A[Start Command] --> B{Cached Access Token Valid?}
    B -- Yes --> C[Use Token]
    B -- No --> D{Have Refresh Token?}
    D -- Yes --> E[Refresh Access Token]
    E -->|Success| C
    E -->|Fail (invalid/expired)| F[Begin Device Code Flow]
    D -- No --> F
    F --> G[Display User Code & URL]
    G --> H[Poll Token Endpoint]
    H -->|Authorized| I[Cache TokenSet]
    H -->|Denied/Timeout| J[Abort with Message]
    I --> C
    C --> K[API / GraphQL Calls]
    K --> L[Render Output]
    L --> M[Exit]

    subgraph Refresh_Check [On Each Command]
        C --> N{Near Expiry?<br/>(threshold)}
        N -- Yes --> E
        N -- No --> C
    end
```

Authentication Sequence (Detailed)
----------------------------------

```mermaid
sequenceDiagram
    autonumber
    participant U as User
    participant CLI as Vantage CLI
    participant Cache as Token Cache
    participant OIDC as OIDC Provider
    participant API as Vantage API

    U->>CLI: Run command
    CLI->>Cache: Load TokenSet(profile)
    alt Access token valid & not near expiry
        CLI->>API: Auth request with access token
        API-->>CLI: Response
        CLI-->>U: Render output
    else Needs refresh or missing token
        opt Has refresh token
            CLI->>OIDC: Refresh (refresh_token)
            alt Refresh success
                OIDC-->>CLI: New TokenSet
                CLI->>Cache: Persist TokenSet (atomic write)
            else Refresh fails
                CLI->>OIDC: Start device code flow
                OIDC-->>CLI: device_code + user_code + verify_uri
                CLI-->>U: Display verification instructions
                loop Poll until authorized or timeout
                    CLI->>OIDC: Poll token endpoint
                    alt Authorized
                        OIDC-->>CLI: TokenSet
                        CLI->>Cache: Persist TokenSet
                    else Pending
                        OIDC-->>CLI: slow_down / authorization_pending
                    end
                end
                alt User completes auth
                    CLI->>API: Auth request with new access token
                    API-->>CLI: Response
                    CLI-->>U: Render output
                else Timeout / denied
                    CLI-->>U: Abort with message
                end
            end
        else No refresh token
            CLI->>OIDC: Start device code flow
            OIDC-->>CLI: device_code + user_code + verify_uri
            CLI-->>U: Display verification instructions
            loop Poll until authorized or timeout
                CLI->>OIDC: Poll token endpoint
                alt Authorized
                    OIDC-->>CLI: TokenSet
                    CLI->>Cache: Persist TokenSet
                else Pending
                    OIDC-->>CLI: authorization_pending
                end
            end
            alt Authorized
                CLI->>API: Auth request with access token
                API-->>CLI: Response
                CLI-->>U: Render output
            else Timeout/Denied
                CLI-->>U: Abort with message
            end
        end
    end
```

Key guarantees:

- No device flow if a valid access token exists.
- Single refresh attempt per command; failures fall back to full device flow.
- Refresh threshold (e.g. < remaining lifetime) triggers proactive renewal.
- Token cache write is atomic (temp file + move) to avoid corruption.
- Abort messages are concise; verbose stack only with `-v`.

Error Handling
--------------

- Domain exceptions map to concise messages
- Traceback only with `-v`
- Non-zero exit on expected user errors

Models
------

- TokenSet: access/refresh/expiry
- Persona: identity claims
- Settings: endpoints & client config

Extensibility
-------------

- New command groups = sub-app registration
- Decorators inject settings/persona
- Output helpers unify formatting

Performance
-----------

- Async network calls
- Early return if tokens valid
- Small JSON read/write footprint

Security
--------

- Token files user-only permissions (expected)
- No token echoing
- Refresh guarded (no infinite retries)

Future Ideas
------------

- Pluggable credential stores
- Streaming subscriptions (GraphQL)
- Verbose timing metrics per command
