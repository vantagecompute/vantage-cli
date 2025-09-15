# CLI Command Reference

This document provides a comprehensive reference for all available CLI commands and their options.


```text
                                                                                                                                                                                
 Usage: vantage [OPTIONS] COMMAND [ARGS]...                                                                                                                  
                                                                                                                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                                                                                                                  │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ version      Show version and exit.                                                                                                                                          │
│ login        Authenticate against the Vantage CLI by obtaining an authentication token.                                                                                      │
│ logout       Log out of the vantage-cli and clear saved user credentials.                                                                                                    │
│ whoami       Display information about the currently authenticated user.                                                                                                     │
│ app          Manage applications                                                                                                                                             │
│ cloud        Manage cloud provider configurations and integrations for your Vantage infrastructure.                                                                          │
│ cluster      Manage Vantage compute clusters for high-performance computing workloads.                                                                                       │
│ config       Manage Vantage CLI configuration and settings.                                                                                                                  │
│ license      Manage software licenses, license servers, and licensing configurations.                                                                                        │
│ network      Manage virtual networks, subnets, and network configurations for cloud infrastructure.                                                                          │
│ notebook     Manage Jupyter notebooks and computational notebooks for data science and research.                                                                             │
│ profile      Manage Vantage CLI profiles to work with different environments and configurations.                                                                             │
│ storage      Manage storage volumes, disks, and storage configurations for cloud infrastructure.                                                                             │
│ deployment   Create and manage application deployments on Vantage compute clusters.                                                                                          │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯


```

## Authentication Commands

### Login

```text
                                                                                                                                                                                
 Usage: vantage login [OPTIONS]                                                                                                                              
                                                                                                                                                                                
 Authenticate against the Vantage CLI by obtaining an authentication token.                                                                                                     
                                                                                                                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --json     -j            Output in JSON format                                                                                                                               │
│ --verbose  -v            Enable verbose terminal output                                                                                                                      │
│ --profile  -p      TEXT  Profile name to use [default: default]                                                                                                              │
│ --help                   Show this message and exit.                                                                                                                         │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯


```

### Logout

```text
                                                                                                                                                                                
 Usage: vantage logout [OPTIONS]                                                                                                                             
                                                                                                                                                                                
 Log out of the vantage-cli and clear saved user credentials.                                                                                                                   
                                                                                                                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --json     -j            Output in JSON format                                                                                                                               │
│ --verbose  -v            Enable verbose terminal output                                                                                                                      │
│ --profile  -p      TEXT  Profile name to use [default: default]                                                                                                              │
│ --help                   Show this message and exit.                                                                                                                         │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯


```

### Whoami

```text
                                                                                                                                                                                
 Usage: vantage whoami [OPTIONS]                                                                                                                             
                                                                                                                                                                                
 Display information about the currently authenticated user.                                                                                                                    
                                                                                                                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --json     -j            Output in JSON format                                                                                                                               │
│ --verbose  -v            Enable verbose terminal output                                                                                                                      │
│ --profile  -p      TEXT  Profile name to use [default: default]                                                                                                              │
│ --help                   Show this message and exit.                                                                                                                         │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯


```

## Version Information

```text
                                                                                                                                                                                
 Usage: vantage version [OPTIONS]                                                                                                                            
                                                                                                                                                                                
 Show version and exit.                                                                                                                                                         
                                                                                                                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --json     -j            Output in JSON format                                                                                                                               │
│ --verbose  -v            Enable verbose terminal output                                                                                                                      │
│ --profile  -p      TEXT  Profile name to use [default: default]                                                                                                              │
│ --help                   Show this message and exit.                                                                                                                         │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯


```

## Application Management

```text
                                                                                                                                                                                
 Usage: vantage app [OPTIONS] COMMAND [ARGS]...                                                                                                              
                                                                                                                                                                                
 Manage applications                                                                                                                                                            
                                                                                                                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                                                                                                                  │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ list   List available applications                                                                                                                                           │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯


```

<details markdown="1" id="app-list">
<summary onclick="window.location.hash='app-list'">Show app list details</summary>

```bash
vantage app list [OPTIONS]
```

**Options:**

- `--json -j            Output in JSON format` - │
- `--verbose -v            Enable verbose terminal output` - │
- `--profile -p      TEXT  Profile name to use` - [default: default]                                                                                                              │
- `--help                   Show this message and` - exit.                                                                                                                         │

</details>

## Cloud Management

```text
                                                                                                                                                                                
 Usage: vantage cloud [OPTIONS] COMMAND [ARGS]...                                                                                                            
                                                                                                                                                                                
 Manage cloud provider configurations and integrations for your Vantage infrastructure.                                                                                         
                                                                                                                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                                                                                                                  │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ add      Add a new cloud configuration.                                                                                                                                      │
│ delete   Delete a cloud configuration.                                                                                                                                       │
│ get      Get details of a specific cloud configuration.                                                                                                                      │
│ list     List all configured cloud providers.                                                                                                                                │
│ update   Update an existing cloud configuration.                                                                                                                             │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯


```

<details markdown="1" id="cloud-add">
<summary onclick="window.location.hash='cloud-add'">Show cloud add details</summary>

```bash
vantage cloud add [OPTIONS] CLOUD_NAME
```

**Arguments:**

- `*` - cloud_name      TEXT  Name of the cloud to add [required]                                                                                                               │

**Options:**

- `--region -r      TEXT  Default region for the cloud` - │
- `--config-file               FILE  Path to cloud configuration file` - │
- `--credentials-file          FILE  Path to credentials file` - │
- `--json -j            Output in JSON format` - │
- `--verbose -v            Enable verbose terminal output` - │
- `--profile -p      TEXT  Profile name to use` - [default: default]                                                                                                  │
- `--help                            Show this message and` - exit.                                                                                                             │

</details>

<details markdown="1" id="cloud-delete">
<summary onclick="window.location.hash='cloud-delete'">Show cloud delete details</summary>

```bash
vantage cloud delete [OPTIONS] CLOUD_NAME
```

**Arguments:**

- `*` - cloud_name      TEXT  Name of the cloud to delete [required]                                                                                                            │

**Options:**

- `--force                             Force deletion without confirmation` - │
- `--remove-credentials                Also remove stored credentials` - │
- `--json -j            Output in JSON format` - │
- `--verbose -v            Enable verbose terminal output` - │
- `--profile -p      TEXT  Profile name to use` - [default: default]                                                                                                   │
- `--help                              Show this message and` - exit.                                                                                                              │

</details>

<details markdown="1" id="cloud-get">
<summary onclick="window.location.hash='cloud-get'">Show cloud get details</summary>

```bash
vantage cloud get [OPTIONS] NAME
```

**Arguments:**

- `*` - name      TEXT  Name of the cloud configuration to retrieve [required]                                                                                                  │

**Options:**

- `--json -j            Output in JSON format` - │
- `--verbose -v            Enable verbose terminal output` - │
- `--profile -p      TEXT  Profile name to use` - [default: default]                                                                                                              │
- `--help                   Show this message and` - exit.                                                                                                                         │

</details>

<details markdown="1" id="cloud-list">
<summary onclick="window.location.hash='cloud-list'">Show cloud list details</summary>

```bash
vantage cloud list [OPTIONS]
```

**Options:**

- `--json -j            Output in JSON format` - │
- `--verbose -v            Enable verbose terminal output` - │
- `--profile -p      TEXT  Profile name to use` - [default: default]                                                                                                              │
- `--help                   Show this message and` - exit.                                                                                                                         │

</details>

<details markdown="1" id="cloud-update">
<summary onclick="window.location.hash='cloud-update'">Show cloud update details</summary>

```bash
vantage cloud update [OPTIONS] CLOUD_NAME
```

**Arguments:**

- `*` - cloud_name      TEXT  Name of the cloud to update [required]                                                                                                            │

**Options:**

- `--provider -p      TEXT  Update cloud provider` - │
- `--region -r      TEXT  Update default region` - │
- `--config-file               FILE  Path to updated configuration file` - │
- `--credentials-file          FILE  Path to updated credentials file` - │
- `--description               TEXT  Update cloud description` - │
- `--json -j            Output in JSON format` - │
- `--verbose -v            Enable verbose terminal output` - │
- `--profile -p      TEXT  Profile name to use` - [default: default]                                                                                                     │
- `--help                            Show this message and` - exit.                                                                                                                │

</details>

## Cluster Management

```text
                                                                                                                                                                                
 Usage: vantage cluster [OPTIONS] COMMAND [ARGS]...                                                                                                          
                                                                                                                                                                                
 Manage Vantage compute clusters for high-performance computing workloads.                                                                                                      
                                                                                                                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                                                                                                                  │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ create       Create a new Vantage cluster.                                                                                                                                   │
│ delete       Delete a Vantage cluster.                                                                                                                                       │
│ get          Get details of a specific Vantage cluster.                                                                                                                      │
│ list         List all Vantage clusters.                                                                                                                                      │
│ federation   Manage Vantage compute federations for distributed workloads.                                                                                                   │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯


```

<details markdown="1" id="cluster-create">
<summary onclick="window.location.hash='cluster-create'">Show cluster create details</summary>

```bash
vantage cluster create [OPTIONS] CLUSTER_NAME
```

**Arguments:**

- `*` - cluster_name      TEXT  Name of the cluster to create [required]                                                                                                        │

**Options:**

- `--config-file          FILE                                                                     Path to configuration file for cluster` - creation.                          │
- `--app` - [slurm-juju-localhost|slurm-microk8s-localhost|slurm-multipass-localhos  Deploy an application after cluster creation.                             │
- `--json -j                                                                               Output in JSON format` - │
- `--verbose -v                                                                               Enable verbose terminal output` - │
- `--profile -p      TEXT                                                                     Profile name to use` - [default: default]                                    │
- `--help                                                                                          Show this message and` - exit.                                               │

</details>

<details markdown="1" id="cluster-delete">
<summary onclick="window.location.hash='cluster-delete'">Show cluster delete details</summary>

```bash
vantage cluster delete [OPTIONS] CLUSTER_NAME
```

**Arguments:**

- `*` - cluster_name      TEXT  Name of the cluster to delete [required]                                                                                                        │

**Options:**

- `--force -f            Skip confirmation prompt` - │
- `--app              TEXT  Cleanup the specified app deployment` - (e.g., slurm-juju-localhost, slurm-multipass-localhost, slurm-microk8s-localhost)                              │
- `--json -j            Output in JSON format` - │
- `--verbose -v            Enable verbose terminal output` - │
- `--profile -p      TEXT  Profile name to use` - [default: default]                                                                                                              │
- `--help                   Show this message and` - exit.                                                                                                                         │

</details>

<details markdown="1" id="cluster-get">
<summary onclick="window.location.hash='cluster-get'">Show cluster get details</summary>

```bash
vantage cluster get [OPTIONS] CLUSTER_NAME
```

**Arguments:**

- `*` - cluster_name      TEXT  Name of the cluster to get details for [required]                                                                                               │

**Options:**

- `--json -j            Output in JSON format` - │
- `--verbose -v            Enable verbose terminal output` - │
- `--profile -p      TEXT  Profile name to use` - [default: default]                                                                                                              │
- `--help                   Show this message and` - exit.                                                                                                                         │

</details>

<details markdown="1" id="cluster-list">
<summary onclick="window.location.hash='cluster-list'">Show cluster list details</summary>

```bash
vantage cluster list [OPTIONS]
```

**Options:**

- `--json -j            Output in JSON format` - │
- `--verbose -v            Enable verbose terminal output` - │
- `--profile -p      TEXT  Profile name to use` - [default: default]                                                                                                              │
- `--help                   Show this message and` - exit.                                                                                                                         │

</details>

<details markdown="1" id="cluster-federation">
<summary onclick="window.location.hash='cluster-federation'">Show cluster federation details</summary>

```bash
vantage cluster federation [OPTIONS] COMMAND
```

**Options:**

- `--help          Show this message and` - exit.                                                                                                                                  │

</details>

## License Management

```text
                                                                                                                                                                                
 Usage: vantage license [OPTIONS] COMMAND [ARGS]...                                                                                                          
                                                                                                                                                                                
 Manage software licenses, license servers, and licensing configurations.                                                                                                       
                                                                                                                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                                                                                                                  │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ server          Manage license servers for software licensing and compliance.                                                                                                │
│ product         Manage license products and software licensing definitions.                                                                                                  │
│ configuration   Manage license configurations and policy settings.                                                                                                           │
│ deployment      Manage license deployments for software distribution and activation.                                                                                         │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯


```

<details markdown="1" id="license-server">
<summary onclick="window.location.hash='license-server'">Show license server details</summary>

```bash
vantage license server [OPTIONS] COMMAND [ARGS]...
```

**Options:**

- `--help          Show this message and` - exit.                                                                                                                                  │

</details>

<details markdown="1" id="license-product">
<summary onclick="window.location.hash='license-product'">Show license product details</summary>

```bash
vantage license product [OPTIONS] COMMAND [ARGS]...
```

**Options:**

- `--help          Show this message and` - exit.                                                                                                                                  │

</details>

<details markdown="1" id="license-configuration">
<summary onclick="window.location.hash='license-configuration'">Show license configuration details</summary>

```bash
vantage license configuration [OPTIONS] COMMAND
```

**Options:**

- `--help          Show this message and` - exit.                                                                                                                                  │

</details>

<details markdown="1" id="license-deployment">
<summary onclick="window.location.hash='license-deployment'">Show license deployment details</summary>

```bash
vantage license deployment [OPTIONS] COMMAND
```

**Options:**

- `--help          Show this message and` - exit.                                                                                                                                  │

</details>

## Network Management

```text
                                                                                                                                                                                
 Usage: vantage network [OPTIONS] COMMAND [ARGS]...                                                                                                          
                                                                                                                                                                                
 Manage virtual networks, subnets, and network configurations for cloud infrastructure.                                                                                         
                                                                                                                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                                                                                                                  │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ attach   Attach a network interface to an instance.                                                                                                                          │
│ create   Create a new virtual network.                                                                                                                                       │
│ delete   Delete a virtual network.                                                                                                                                           │
│ detach   Detach a network interface from an instance.                                                                                                                        │
│ get      Get details of a specific virtual network.                                                                                                                          │
│ list     List all virtual networks.                                                                                                                                          │
│ update   Update a virtual network configuration.                                                                                                                             │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯


```

<details markdown="1" id="network-attach">
<summary onclick="window.location.hash='network-attach'">Show network attach details</summary>

```bash
vantage network attach [OPTIONS] NETWORK_ID
```

**Arguments:**

- `*` - network_id       TEXT  ID of the network to attach [required]                                                                                                           │
- `*` - instance_id      TEXT  ID of the instance to attach network to [required]                                                                                               │

**Options:**

- `--subnet-id -s      TEXT  Specific subnet ID to attach` - │
- `--assign-public-ip                Assign a public IP address` - │
- `--json -j            Output in JSON format` - │
- `--verbose -v            Enable verbose terminal output` - │
- `--profile -p      TEXT  Profile name to use` - [default: default]                                                                                                     │
- `--help                            Show this message and` - exit.                                                                                                                │

</details>

<details markdown="1" id="network-create">
<summary onclick="window.location.hash='network-create'">Show network create details</summary>

```bash
vantage network create [OPTIONS] NAME
```

**Arguments:**

- `*` - name      TEXT  Name of the network to create [required]                                                                                                                │

**Options:**

- `--cidr -c      TEXT  CIDR block for the network` - [default: 10.0.0.0/16]                                                                                               │
- `--region -r      TEXT  Region for the network` - │
- `--enable-dns                 Enable DNS resolution` - [default: True]                                                                                                           │
- `--description -d      TEXT  Description of the network` - │
- `--json -j            Output in JSON format` - │
- `--verbose -v            Enable verbose terminal output` - │
- `--profile -p      TEXT  Profile name to use` - [default: default]                                                                                                          │
- `--help                       Show this message and` - exit.                                                                                                                     │

</details>

<details markdown="1" id="network-delete">
<summary onclick="window.location.hash='network-delete'">Show network delete details</summary>

```bash
vantage network delete [OPTIONS] NETWORK_ID
```

**Arguments:**

- `*` - network_id      TEXT  ID of the network to delete [required]                                                                                                            │

**Options:**

- `--force -f            Skip confirmation prompt` - │
- `--json -j            Output in JSON format` - │
- `--verbose -v            Enable verbose terminal output` - │
- `--profile -p      TEXT  Profile name to use` - [default: default]                                                                                                              │
- `--help                   Show this message and` - exit.                                                                                                                         │

</details>

<details markdown="1" id="network-detach">
<summary onclick="window.location.hash='network-detach'">Show network detach details</summary>

```bash
vantage network detach [OPTIONS] NETWORK_ID
```

**Arguments:**

- `*` - network_id       TEXT  ID of the network to detach [required]                                                                                                           │
- `*` - instance_id      TEXT  ID of the instance to detach network from [required]                                                                                             │

**Options:**

- `--force -f            Force detachment without graceful shutdown` - │
- `--json -j            Output in JSON format` - │
- `--verbose -v            Enable verbose terminal output` - │
- `--profile -p      TEXT  Profile name to use` - [default: default]                                                                                                              │
- `--help                   Show this message and` - exit.                                                                                                                         │

</details>

<details markdown="1" id="network-get">
<summary onclick="window.location.hash='network-get'">Show network get details</summary>

```bash
vantage network get [OPTIONS] NETWORK_ID
```

**Arguments:**

- `*` - network_id      TEXT  ID of the network to retrieve [required]                                                                                                          │

**Options:**

- `--json -j            Output in JSON format` - │
- `--verbose -v            Enable verbose terminal output` - │
- `--profile -p      TEXT  Profile name to use` - [default: default]                                                                                                              │
- `--help                   Show this message and` - exit.                                                                                                                         │

</details>

<details markdown="1" id="network-list">
<summary onclick="window.location.hash='network-list'">Show network list details</summary>

```bash
vantage network list [OPTIONS]
```

**Options:**

- `--region -r      TEXT     Filter by region` - │
- `--status -s      TEXT     Filter by status` - │
- `--limit -l      INTEGER  Maximum number of networks to return` - [default: 10]                                                                                               │
- `--json -j               Output in JSON format` - │
- `--verbose -v               Enable verbose terminal output` - │
- `--profile -p      TEXT     Profile name to use` - [default: default]                                                                                                           │
- `--help                      Show this message and` - exit.                                                                                                                      │

</details>

<details markdown="1" id="network-update">
<summary onclick="window.location.hash='network-update'">Show network update details</summary>

```bash
vantage network update [OPTIONS] NETWORK_ID
```

**Arguments:**

- `*` - network_id      TEXT  ID of the network to update [required]                                                                                                            │

**Options:**

- `--name -n                   TEXT  New name for the network` - │
- `--description -d                   TEXT  New description` - │
- `--enable-dns       --disable-dns          Enable or disable DNS resolution` - │
- `--json -j                         Output in JSON format` - │
- `--verbose -v                         Enable verbose terminal output` - │
- `--profile -p                   TEXT  Profile name to use` - [default: default]                                                                                             │
- `--help                                    Show this message and` - exit.                                                                                                        │

</details>

## Notebook Commands

```text
                                                                                                                                                                                
 Usage: vantage notebook [OPTIONS] COMMAND [ARGS]...                                                                                                         
                                                                                                                                                                                
 Manage Jupyter notebooks and computational notebooks for data science and research.                                                                                            
                                                                                                                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                                                                                                                  │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ create   Create a new Jupyter notebook server.                                                                                                                               │
│ delete   Delete notebook server.                                                                                                                                             │
│ get      Get notebook server details.                                                                                                                                        │
│ list     List notebook servers.                                                                                                                                              │
│ update   Update a Jupyter notebook configuration.                                                                                                                            │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯


```

<details markdown="1" id="notebook-create">
<summary onclick="window.location.hash='notebook-create'">Show notebook create details</summary>

```bash
vantage notebook create [OPTIONS] NAME
```

**Arguments:**

- `*` - name      TEXT  Name of the notebook server [required]                                                                                                                  │

**Options:**

- `--cpu                INTEGER  Number of CPU cores` - │
- `--memory             FLOAT    Memory in MB` - │
- `--gpus               INTEGER  Number of GPUs` - │
- `--json -j               Output in JSON format` - │
- `--verbose -v               Enable verbose terminal output` - │
- `--profile -p      TEXT     Profile name to use` - [default: default]                                                                                                      │
- `--help                        Show this message and` - exit.                                                                                                                 │

</details>

<details markdown="1" id="notebook-delete">
<summary onclick="window.location.hash='notebook-delete'">Show notebook delete details</summary>

```bash
vantage notebook delete [OPTIONS] NAME
```

**Arguments:**

- `*` - name      TEXT  Notebook server name [required]                                                                                                                         │

**Options:**

- `--cluster -c      TEXT  Cluster name` - │
- `--force -f            Force deletion without confirmation` - │
- `--json -j            Output in JSON format` - │
- `--verbose -v            Enable verbose terminal output` - │
- `--profile -p      TEXT  Profile name to use` - [default: default]                                                                                                              │
- `--help                   Show this message and` - exit.                                                                                                                         │

</details>

<details markdown="1" id="notebook-get">
<summary onclick="window.location.hash='notebook-get'">Show notebook get details</summary>

```bash
vantage notebook get [OPTIONS] NAME
```

**Arguments:**

- `*` - name      TEXT  Notebook server name [required]                                                                                                                         │

**Options:**

- `--cluster -c      TEXT  Cluster name` - │
- `--json -j            Output in JSON format` - │
- `--verbose -v            Enable verbose terminal output` - │
- `--profile -p      TEXT  Profile name to use` - [default: default]                                                                                                              │
- `--help                   Show this message and` - exit.                                                                                                                         │

</details>

<details markdown="1" id="notebook-list">
<summary onclick="window.location.hash='notebook-list'">Show notebook list details</summary>

```bash
vantage notebook list [OPTIONS]
```

**Options:**

- `--cluster -c      TEXT     Filter by cluster name` - │
- `--status -s      TEXT     Filter by notebook status` - │
- `--kernel -k      TEXT     Filter by kernel type` - │
- `--limit -l      INTEGER  Maximum number of notebooks to return` - │
- `--json -j               Output in JSON format` - │
- `--verbose -v               Enable verbose terminal output` - │
- `--profile -p      TEXT     Profile name to use` - [default: default]                                                                                                           │
- `--help                      Show this message and` - exit.                                                                                                                      │

</details>

<details markdown="1" id="notebook-update">
<summary onclick="window.location.hash='notebook-update'">Show notebook update details</summary>

```bash
vantage notebook update [OPTIONS] NOTEBOOK_ID
```

**Arguments:**

- `*` - notebook_id      TEXT  ID of the notebook to update [required]                                                                                                          │

**Options:**

- `--name -n      TEXT  New name for the notebook` - │
- `--description -d      TEXT  New description` - │
- `--kernel -k      TEXT  New kernel type` - │
- `--json -j            Output in JSON format` - │
- `--verbose -v            Enable verbose terminal output` - │
- `--profile -p      TEXT  Profile name to use` - [default: default]                                                                                                          │
- `--help                       Show this message and` - exit.                                                                                                                     │

</details>

## Profile Management

```text
                                                                                                                                                                                
 Usage: vantage profile [OPTIONS] COMMAND [ARGS]...                                                                                                          
                                                                                                                                                                                
 Manage Vantage CLI profiles to work with different environments and configurations.                                                                                            
                                                                                                                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                                                                                                                  │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ create   Create a new Vantage CLI profile.                                                                                                                                   │
│ delete   Delete a Vantage CLI profile.                                                                                                                                       │
│ get      Get details of a specific Vantage CLI profile.                                                                                                                      │
│ list     List all Vantage CLI profiles.                                                                                                                                      │
│ use      Activate a profile for use in the current session.                                                                                                                  │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯


```

<details markdown="1" id="profile-create">
<summary onclick="window.location.hash='profile-create'">Show profile create details</summary>

```bash
vantage profile create [OPTIONS] PROFILE_NAME
```

**Arguments:**

- `*` - profile_name      TEXT  Name of the profile to create [required]                                                                                                        │

**Options:**

- `--api-url                TEXT     API base URL` - [default: https://apis.vantagecompute.ai]                                                                                     │
- `--tunnel-url             TEXT     Tunnel API URL` - [default: https://tunnel.vantagecompute.ai]                                                                                 │
- `--oidc-url               TEXT     OIDC base URL` - [default: https://auth.vantagecompute.ai]                                                                                    │
- `--client-id              TEXT     OIDC client ID` - [default: default]                                                                                                          │
- `--max-poll-time          INTEGER  OIDC max poll time in seconds` - [default: 300]                                                                                               │
- `--force -f               Overwrite existing profile` - │
- `--activate                        Activate this profile after creation` - │
- `--json -j               Output in JSON format` - │
- `--verbose -v               Enable verbose terminal output` - │
- `--help                            Show this message and` - exit.                                                                                                                │

</details>

<details markdown="1" id="profile-delete">
<summary onclick="window.location.hash='profile-delete'">Show profile delete details</summary>

```bash
vantage profile delete [OPTIONS] PROFILE_NAME
```

**Arguments:**

- `*` - profile_name      TEXT  Name of the profile to delete [required]                                                                                                        │

**Options:**

- `--force -f        Skip confirmation prompt` - │
- `--json -j        Output in JSON format` - │
- `--verbose -v        Enable verbose terminal output` - │
- `--help               Show this message and` - exit.                                                                                                                             │

</details>

<details markdown="1" id="profile-get">
<summary onclick="window.location.hash='profile-get'">Show profile get details</summary>

```bash
vantage profile get [OPTIONS] PROFILE_NAME
```

**Arguments:**

- `*` - profile_name      TEXT  Name of the profile to get details for [required]                                                                                               │

**Options:**

- `--json -j        Output in JSON format` - │
- `--verbose -v        Enable verbose terminal output` - │
- `--help               Show this message and` - exit.                                                                                                                             │

</details>

<details markdown="1" id="profile-list">
<summary onclick="window.location.hash='profile-list'">Show profile list details</summary>

```bash
vantage profile list [OPTIONS]
```

**Options:**

- `--json -j        Output in JSON format` - │
- `--verbose -v        Enable verbose terminal output` - │
- `--help               Show this message and` - exit.                                                                                                                             │

</details>

<details markdown="1" id="profile-use">
<summary onclick="window.location.hash='profile-use'">Show profile use details</summary>

```bash
vantage profile use [OPTIONS] PROFILE_NAME
```

**Arguments:**

- `*` - profile_name      TEXT  Name of the profile to activate [required]                                                                                                      │

**Options:**

- `--json -j        Output in JSON format` - │
- `--verbose -v        Enable verbose terminal output` - │
- `--help               Show this message and` - exit.                                                                                                                             │

</details>

## Storage Management

```text
                                                                                                                                                                                
 Usage: vantage storage [OPTIONS] COMMAND [ARGS]...                                                                                                          
                                                                                                                                                                                
 Manage storage volumes, disks, and storage configurations for cloud infrastructure.                                                                                            
                                                                                                                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                                                                                                                  │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ attach   Attach a storage volume to an instance.                                                                                                                             │
│ create   Create a new storage volume.                                                                                                                                        │
│ delete   Delete a storage volume.                                                                                                                                            │
│ detach   Detach a storage volume from an instance.                                                                                                                           │
│ get      Get details of a specific storage volume.                                                                                                                           │
│ list     List all storage volumes.                                                                                                                                           │
│ update   Update a storage volume configuration.                                                                                                                              │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯


```

<details markdown="1" id="storage-attach">
<summary onclick="window.location.hash='storage-attach'">Show storage attach details</summary>

```bash
vantage storage attach [OPTIONS] STORAGE_ID
```

**Arguments:**

- `*` - storage_id       TEXT  ID of the storage volume to attach [required]                                                                                                    │
- `*` - instance_id      TEXT  ID of the instance to attach storage to [required]                                                                                               │

**Options:**

- `--mount-point -m      TEXT  Mount point for the storage` - [default: /data]                                                                                                    │
- `--read-only -r            Attach storage in read-only mode` - │
- `--json -j            Output in JSON format` - │
- `--verbose -v            Enable verbose terminal output` - │
- `--profile -p      TEXT  Profile name to use` - [default: default]                                                                                                          │
- `--help                       Show this message and` - exit.                                                                                                                     │

</details>

<details markdown="1" id="storage-create">
<summary onclick="window.location.hash='storage-create'">Show storage create details</summary>

```bash
vantage storage create [OPTIONS] NAME
```

**Arguments:**

- `*` - name      TEXT  Name of the storage volume to create [required]                                                                                                         │

**Options:**

- `--size -s      INTEGER  Size of the storage volume in GB` - [default: 10]                                                                                               │
- `--type -t      TEXT     Storage type` - (ssd, hdd, nvme) [default: ssd]                                                                                                 │
- `--zone -z      TEXT     Availability zone for the storage` - │
- `--description -d      TEXT     Description of the storage volume` - │
- `--json -j               Output in JSON format` - │
- `--verbose -v               Enable verbose terminal output` - │
- `--profile -p      TEXT     Profile name to use` - [default: default]                                                                                                       │
- `--help                          Show this message and` - exit.                                                                                                                  │

</details>

<details markdown="1" id="storage-delete">
<summary onclick="window.location.hash='storage-delete'">Show storage delete details</summary>

```bash
vantage storage delete [OPTIONS] STORAGE_ID
```

**Arguments:**

- `*` - storage_id      TEXT  ID of the storage volume to delete [required]                                                                                                     │

**Options:**

- `--force -f            Skip confirmation prompt` - │
- `--json -j            Output in JSON format` - │
- `--verbose -v            Enable verbose terminal output` - │
- `--profile -p      TEXT  Profile name to use` - [default: default]                                                                                                              │
- `--help                   Show this message and` - exit.                                                                                                                         │

</details>

<details markdown="1" id="storage-detach">
<summary onclick="window.location.hash='storage-detach'">Show storage detach details</summary>

```bash
vantage storage detach [OPTIONS] STORAGE_ID
```

**Arguments:**

- `*` - storage_id      TEXT  ID of the storage volume to detach [required]                                                                                                     │

**Options:**

- `--force -f            Force detachment without graceful unmounting` - │
- `--json -j            Output in JSON format` - │
- `--verbose -v            Enable verbose terminal output` - │
- `--profile -p      TEXT  Profile name to use` - [default: default]                                                                                                              │
- `--help                   Show this message and` - exit.                                                                                                                         │

</details>

<details markdown="1" id="storage-get">
<summary onclick="window.location.hash='storage-get'">Show storage get details</summary>

```bash
vantage storage get [OPTIONS] STORAGE_ID
```

**Arguments:**

- `*` - storage_id      TEXT  ID of the storage volume to retrieve [required]                                                                                                   │

**Options:**

- `--json -j            Output in JSON format` - │
- `--verbose -v            Enable verbose terminal output` - │
- `--profile -p      TEXT  Profile name to use` - [default: default]                                                                                                              │
- `--help                   Show this message and` - exit.                                                                                                                         │

</details>

<details markdown="1" id="storage-list">
<summary onclick="window.location.hash='storage-list'">Show storage list details</summary>

```bash
vantage storage list [OPTIONS]
```

**Options:**

- `--zone -z      TEXT     Filter by availability zone` - │
- `--type -t      TEXT     Filter by storage type` - │
- `--status -s      TEXT     Filter by status` - │
- `--limit -l      INTEGER  Maximum number of storage volumes to return` - [default: 10]                                                                                        │
- `--json -j               Output in JSON format` - │
- `--verbose -v               Enable verbose terminal output` - │
- `--profile -p      TEXT     Profile name to use` - [default: default]                                                                                                           │
- `--help                      Show this message and` - exit.                                                                                                                      │

</details>

<details markdown="1" id="storage-update">
<summary onclick="window.location.hash='storage-update'">Show storage update details</summary>

```bash
vantage storage update [OPTIONS] STORAGE_ID
```

**Arguments:**

- `*` - storage_id      TEXT  ID of the storage volume to update [required]                                                                                                     │

**Options:**

- `--name -n      TEXT     New name for the storage volume` - │
- `--size -s      INTEGER  New size in GB` - (expansion only)                                                                                                              │
- `--description -d      TEXT     New description` - │
- `--iops                 INTEGER  New IOPS setting` - │
- `--json -j               Output in JSON format` - │
- `--verbose -v               Enable verbose terminal output` - │
- `--profile -p      TEXT     Profile name to use` - [default: default]                                                                                                       │
- `--help                          Show this message and` - exit.                                                                                                                  │

</details>

## Deployment Commands

```text
                                                                                                                                                                                
 Usage: vantage deployment [OPTIONS] COMMAND [ARGS]...                                                                                                       
                                                                                                                                                                                
 Create and manage application deployments on Vantage compute clusters.                                                                                                         
                                                                                                                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                                                                                                                  │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ list     List all active deployments from ~/.vantage-cli/deployments.yaml.                                                                                                   │
│ create   Create a slurm cluster deployment and link it to a cluster entity in Vantage.                                                                                       │
│ delete   Delete a deployment and clean up its resources.                                                                                                                     │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯


```

<details markdown="1" id="deployment-list">
<summary onclick="window.location.hash='deployment-list'">Show deployment list details</summary>

```bash
vantage deployment list [OPTIONS]
```

**Options:**

- `--json -j            Output in JSON format` - │
- `--verbose -v            Enable verbose terminal output` - │
- `--profile -p      TEXT  Profile name to use` - [default: default]                                                                                                              │
- `--help                   Show this message and` - exit.                                                                                                                         │

</details>

<details markdown="1" id="deployment-create">
<summary onclick="window.location.hash='deployment-create'">Show deployment create details</summary>

```bash
vantage deployment create [OPTIONS] APP_NAME
```

**Arguments:**

- `*` - app_name          TEXT  Name of the cluster infrastructure application to deploy [required]                                                                             │
- `*` - cluster_name      TEXT  Name of the cluster in Vantage you would like to link to [required]                                                                             │

**Options:**

- `--name             TEXT  Custom name for the deployment` - (default: &lt;app&gt;-&lt;cluster&gt;-&lt;timestamp&gt;)                                                                               │
- `--dev-run                Use dummy cluster data for local development` - │
- `--json -j            Output in JSON format` - │
- `--verbose -v            Enable verbose terminal output` - │
- `--profile -p      TEXT  Profile name to use` - [default: default]                                                                                                              │
- `--help                   Show this message and` - exit.                                                                                                                         │

</details>

<details markdown="1" id="deployment-delete">
<summary onclick="window.location.hash='deployment-delete'">Show deployment delete details</summary>

```bash
vantage deployment delete [OPTIONS] DEPLOYMENT_ID
```

**Arguments:**

- `*` - deployment_id      TEXT  Deployment ID to delete [required]                                                                                                             │

**Options:**

- `--force -f            Skip confirmation prompt` - │
- `--json -j            Output in JSON format` - │
- `--verbose -v            Enable verbose terminal output` - │
- `--profile -p      TEXT  Profile name to use` - [default: default]                                                                                                              │
- `--help                   Show this message and` - exit.                                                                                                                         │

</details>

## Configuration Management

<details markdown="1" id="config-clear">
<summary onclick="window.location.hash='config-clear'">Show config clear details</summary>

```bash
vantage config clear [OPTIONS]
```

**Options:**

- `--force -f            Skip confirmation prompt` - │
- `--json -j            Output in JSON format` - │
- `--verbose -v            Enable verbose terminal output` - │
- `--profile -p      TEXT  Profile name to use` - [default: default]                                                                                                              │
- `--help                   Show this message and` - exit.                                                                                                                         │

</details>
