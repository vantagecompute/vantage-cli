---
title: Notebooks
description: Notebooks Lifecycle in Vantage CLI
---

## Notebook Overview

The Vantage CLI supports Notebook Server lifecycle management subcommand `notebook` supports CRUD operations; create, delete, get, update, list.

### Create a Notebook

```bash
vantage notebook create mynote00 --cluster multipass-00 --partition compute
```

### List Notebooks

```bash
vantage notebooks

                                             Notebook Servers                                              
┏━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ Name        ┃ Cluster        ┃ Partition ┃ Owner           ┃ Server URL     ┃ SLURM Job ID ┃ Created    ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ mynote00    │ multipass-00   │ compute   │ james@vantagec… │ https://multi..│ 1            │ 2025-09-15 │
│ nvidia-t4   │ aws-us-east-1  │ slurmd    │ james@vantagec… │ https://aws-u..│ 1            │ 2025-09-15 │
└─────────────┴────────────────┴───────────┴─────────────────┴────────────────┴──────────────┴────────────┘
                                               Items: 2 of 2                                               
```

### Get a Notebook

```bash
vantage notebook get mynote00

╭───────────────────────────────── Notebook Server: asetaset ──────────────────────────────────╮
│ Name: mynote00                                                                               │
│ ID: 361                                                                                      │
│ Cluster: multipass-00                                                                        │
│ Partition: compute                                                                           │
│ Owner: james@vantagecompute.ai                                                               │
│ Server URL: https://multipass-00-0d317c8b-1cfe-423e-a518-57f97fd50c6e.vantagecompute.ai      │
│ SLURM Job ID: 1                                                                              │
│ Created: 2025-09-15T03:48:28.179244+00:00                                                    │
│ Updated: 2025-09-15T03:48:28.179244+00:00                                                    │
╰──────────────────────────────────────────────────────────────────────────────────────────────╯
```

### Delete a Notebook

```bash
vantage notebook delete mynote00

Are you sure you want to delete notebook server 'mynote00'? [y/N]: y
✓ Notebook Server has been deleted.
```

### Update a Notebook