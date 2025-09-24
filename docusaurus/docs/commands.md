# CLI Command Reference

import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';
import CodeBlock from '@theme/CodeBlock';

This document provides a comprehensive reference for all available CLI commands and their options.


<CodeBlock language="text" title="CLI Help">
                                                                                
 Usage: vantage [OPTIONS] COMMAND [ARGS]...                  
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ version      Show version and exit.                                          │
│ login        Authenticate against the Vantage CLI by obtaining an            │
│              authentication token.                                           │
│ logout       Log out of the vantage-cli and clear saved user credentials.    │
│ whoami       Display information about the currently authenticated user.     │
│ app          Manage applications                                             │
│ cloud        Manage cloud provider configurations and integrations for your  │
│              Vantage infrastructure.                                         │
│ cluster      Manage Vantage compute clusters for high-performance computing  │
│              workloads.                                                      │
│ config       Manage Vantage CLI configuration and settings.                  │
│ license      Manage software licenses, license servers, and licensing        │
│              configurations.                                                 │
│ network      Manage virtual networks, subnets, and network configurations    │
│              for cloud infrastructure.                                       │
│ notebook     Manage Jupyter notebooks and computational notebooks for data   │
│              science and research.                                           │
│ profile      Manage Vantage CLI profiles to work with different environments │
│              and configurations.                                             │
│ storage      Manage storage volumes, disks, and storage configurations for   │
│              cloud infrastructure.                                           │
│ deployment   Create and manage application deployments on Vantage compute    │
│              clusters.                                                       │
╰──────────────────────────────────────────────────────────────────────────────╯


</CodeBlock>

## Authentication Commands

### Login

<CodeBlock language="text" title="CLI Help">
                                                                                
 Usage: vantage login [OPTIONS]                              
                                                                                
 Authenticate against the Vantage CLI by obtaining an authentication token.     
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --json     -j            Output in JSON format                               │
│ --verbose  -v            Enable verbose terminal output                      │
│ --profile  -p      TEXT  Profile name to use [default: default]              │
│ --help                   Show this message and exit.                         │
╰──────────────────────────────────────────────────────────────────────────────╯


</CodeBlock>

### Logout

<CodeBlock language="text" title="CLI Help">
                                                                                
 Usage: vantage logout [OPTIONS]                             
                                                                                
 Log out of the vantage-cli and clear saved user credentials.                   
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --json     -j            Output in JSON format                               │
│ --verbose  -v            Enable verbose terminal output                      │
│ --profile  -p      TEXT  Profile name to use [default: default]              │
│ --help                   Show this message and exit.                         │
╰──────────────────────────────────────────────────────────────────────────────╯


</CodeBlock>

### Whoami

<CodeBlock language="text" title="CLI Help">
                                                                                
 Usage: vantage whoami [OPTIONS]                             
                                                                                
 Display information about the currently authenticated user.                    
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --json     -j            Output in JSON format                               │
│ --verbose  -v            Enable verbose terminal output                      │
│ --profile  -p      TEXT  Profile name to use [default: default]              │
│ --help                   Show this message and exit.                         │
╰──────────────────────────────────────────────────────────────────────────────╯


</CodeBlock>

## Version Information

<CodeBlock language="text" title="CLI Help">
                                                                                
 Usage: vantage version [OPTIONS]                            
                                                                                
 Show version and exit.                                                         
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --json     -j            Output in JSON format                               │
│ --verbose  -v            Enable verbose terminal output                      │
│ --profile  -p      TEXT  Profile name to use [default: default]              │
│ --help                   Show this message and exit.                         │
╰──────────────────────────────────────────────────────────────────────────────╯


</CodeBlock>

## App Management

<Tabs>
<TabItem value="app" label="🔹 app">

<CodeBlock language="text" title="CLI Help">
                                                                                
 Usage: vantage app [OPTIONS] COMMAND [ARGS]...              
                                                                                
 Manage applications                                                            
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ list   List available applications                                           │
╰──────────────────────────────────────────────────────────────────────────────╯


</CodeBlock>

</TabItem>
<TabItem value="list" label="list">

<CodeBlock language="text" title="CLI Help">
                                                                                
 Usage: vantage app list [OPTIONS]                           
                                                                                
 List available applications                                                    
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --json     -j            Output in JSON format                               │
│ --verbose  -v            Enable verbose terminal output                      │
│ --profile  -p      TEXT  Profile name to use [default: default]              │
│ --help                   Show this message and exit.                         │
╰──────────────────────────────────────────────────────────────────────────────╯


</CodeBlock>


</TabItem>
</Tabs>

## Cloud Management

<Tabs>
<TabItem value="cloud" label="🔹 cloud">

<CodeBlock language="text" title="CLI Help">
                                                                                
 Usage: vantage cloud [OPTIONS] COMMAND [ARGS]...            
                                                                                
 Manage cloud provider configurations and integrations for your Vantage         
 infrastructure.                                                                
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ add      Add a new cloud configuration.                                      │
│ delete   Delete a cloud configuration.                                       │
│ get      Get details of a specific cloud configuration.                      │
│ list     List all configured cloud providers.                                │
│ update   Update an existing cloud configuration.                             │
╰──────────────────────────────────────────────────────────────────────────────╯


</CodeBlock>

</TabItem>
<TabItem value="add" label="add">

<CodeBlock language="text" title="CLI Help">
                                                                                
 Usage: vantage cloud add [OPTIONS] CLOUD_NAME               
                                                                                
 Add a new cloud configuration.                                                 
                                                                                
╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    cloud_name      TEXT  Name of the cloud to add [required]               │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ *  --provider          -p      TEXT  Cloud provider (aws, gcp, azure, etc.)  │
│                                      [required]                              │
│    --region            -r      TEXT  Default region for the cloud            │
│    --config-file               FILE  Path to cloud configuration file        │
│    --credentials-file          FILE  Path to credentials file                │
│    --json              -j            Output in JSON format                   │
│    --verbose           -v            Enable verbose terminal output          │
│    --profile           -p      TEXT  Profile name to use [default: default]  │
│    --help                            Show this message and exit.             │
╰──────────────────────────────────────────────────────────────────────────────╯


</CodeBlock>


</TabItem>
<TabItem value="delete" label="delete">

<CodeBlock language="text" title="CLI Help">
                                                                                
 Usage: vantage cloud delete [OPTIONS] CLOUD_NAME            
                                                                                
 Delete a cloud configuration.                                                  
                                                                                
╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    cloud_name      TEXT  Name of the cloud to delete [required]            │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --force                             Force deletion without confirmation      │
│ --remove-credentials                Also remove stored credentials           │
│ --json                -j            Output in JSON format                    │
│ --verbose             -v            Enable verbose terminal output           │
│ --profile             -p      TEXT  Profile name to use [default: default]   │
│ --help                              Show this message and exit.              │
╰──────────────────────────────────────────────────────────────────────────────╯


</CodeBlock>


</TabItem>
<TabItem value="get" label="get">

<CodeBlock language="text" title="CLI Help">
                                                                                
 Usage: vantage cloud get [OPTIONS] NAME                     
                                                                                
 Get details of a specific cloud configuration.                                 
                                                                                
 Retrieves and displays detailed information about a specific cloud provider    
 configuration including credentials, region settings, and connection status.   
 Args:     ctx: The Typer context     name: Name of the cloud configuration to  
 retrieve                                                                       
                                                                                
╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    name      TEXT  Name of the cloud configuration to retrieve [required]  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --json     -j            Output in JSON format                               │
│ --verbose  -v            Enable verbose terminal output                      │
│ --profile  -p      TEXT  Profile name to use [default: default]              │
│ --help                   Show this message and exit.                         │
╰──────────────────────────────────────────────────────────────────────────────╯


</CodeBlock>


</TabItem>
<TabItem value="list" label="list">

<CodeBlock language="text" title="CLI Help">
                                                                                
 Usage: vantage cloud list [OPTIONS] COMMAND_START_TIME      
                                                                                
 List all configured cloud providers.                                           
                                                                                
 Displays a list of all cloud provider configurations including their status,   
 regions, and basic connection information.                                     
 Args:     ctx: The Typer context     command_start_time: Time when the command 
 started execution                                                              
                                                                                
╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    command_start_time      FLOAT  [required]                               │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --json     -j            Output in JSON format                               │
│ --verbose  -v            Enable verbose terminal output                      │
│ --profile  -p      TEXT  Profile name to use [default: default]              │
│ --help                   Show this message and exit.                         │
╰──────────────────────────────────────────────────────────────────────────────╯


</CodeBlock>


</TabItem>
<TabItem value="update" label="update">

<CodeBlock language="text" title="CLI Help">
                                                                                
 Usage: vantage cloud update [OPTIONS] CLOUD_NAME            
                                                                                
 Update an existing cloud configuration.                                        
                                                                                
╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    cloud_name      TEXT  Name of the cloud to update [required]            │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --provider          -p      TEXT  Update cloud provider                      │
│ --region            -r      TEXT  Update default region                      │
│ --config-file               FILE  Path to updated configuration file         │
│ --credentials-file          FILE  Path to updated credentials file           │
│ --description               TEXT  Update cloud description                   │
│ --json              -j            Output in JSON format                      │
│ --verbose           -v            Enable verbose terminal output             │
│ --profile           -p      TEXT  Profile name to use [default: default]     │
│ --help                            Show this message and exit.                │
╰──────────────────────────────────────────────────────────────────────────────╯


</CodeBlock>


</TabItem>
</Tabs>

## Cluster Management

<Tabs>
<TabItem value="cluster" label="🔹 cluster">

<CodeBlock language="text" title="CLI Help">
                                                                                
 Usage: vantage cluster [OPTIONS] COMMAND [ARGS]...          
                                                                                
 Manage Vantage compute clusters for high-performance computing workloads.      
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ create       Create a new Vantage cluster.                                   │
│ delete       Delete a Vantage cluster.                                       │
│ get          Get details of a specific Vantage cluster.                      │
│ list         List all Vantage clusters.                                      │
│ federation   Manage Vantage compute federations for distributed workloads.   │
╰──────────────────────────────────────────────────────────────────────────────╯


</CodeBlock>

</TabItem>
<TabItem value="create" label="create">

<CodeBlock language="text" title="CLI Help">
                                                                                
 Usage: vantage cluster create [OPTIONS] CLUSTER_NAME        
                                                                                
 Create a new Vantage cluster.                                                  
                                                                                
╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    cluster_name      TEXT  Name of the cluster to create [required]        │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ *  --cloud        -c      [maas|localhost|aws|gcp|  Cloud to use for         │
│                           azure|on-premises|k8s]    deployment.              │
│                                                     [required]               │
│    --config-file          FILE                      Path to configuration    │
│                                                     file for cluster         │
│                                                     creation.                │
│    --app                  [slurm-microk8s-localhos  Deploy an application    │
│                           t|slurm-juju-localhost|s  after cluster creation.  │
│                           lurm-multipass-localhost                           │
│                           |jupyterhub-microk8s-loc                           │
│                           alhost]                                            │
│    --json         -j                                Output in JSON format    │
│    --verbose      -v                                Enable verbose terminal  │
│                                                     output                   │
│    --profile      -p      TEXT                      Profile name to use      │
│                                                     [default: default]       │
│    --help                                           Show this message and    │
│                                                     exit.                    │
╰──────────────────────────────────────────────────────────────────────────────╯


</CodeBlock>


</TabItem>
<TabItem value="delete" label="delete">

<CodeBlock language="text" title="CLI Help">
                                                                                
 Usage: vantage cluster delete [OPTIONS] CLUSTER_NAME        
                                                                                
 Delete a Vantage cluster.                                                      
                                                                                
╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    cluster_name      TEXT  Name of the cluster to delete [required]        │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --force    -f            Skip confirmation prompt                            │
│ --app              TEXT  Cleanup the specified app deployment (e.g.,         │
│                          slurm-juju-localhost, slurm-multipass-localhost,    │
│                          slurm-microk8s-localhost)                           │
│ --json     -j            Output in JSON format                               │
│ --verbose  -v            Enable verbose terminal output                      │
│ --profile  -p      TEXT  Profile name to use [default: default]              │
│ --help                   Show this message and exit.                         │
╰──────────────────────────────────────────────────────────────────────────────╯


</CodeBlock>


</TabItem>
<TabItem value="get" label="get">

<CodeBlock language="text" title="CLI Help">
                                                                                
 Usage: vantage cluster get [OPTIONS] CLUSTER_NAME           
                                                                                
 Get details of a specific Vantage cluster.                                     
                                                                                
╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    cluster_name      TEXT  Name of the cluster to get details for          │
│                              [required]                                      │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --json     -j            Output in JSON format                               │
│ --verbose  -v            Enable verbose terminal output                      │
│ --profile  -p      TEXT  Profile name to use [default: default]              │
│ --help                   Show this message and exit.                         │
╰──────────────────────────────────────────────────────────────────────────────╯


</CodeBlock>


</TabItem>
<TabItem value="list" label="list">

<CodeBlock language="text" title="CLI Help">
                                                                                
 Usage: vantage cluster list [OPTIONS]                       
                                                                                
 List all Vantage clusters.                                                     
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --json     -j            Output in JSON format                               │
│ --verbose  -v            Enable verbose terminal output                      │
│ --profile  -p      TEXT  Profile name to use [default: default]              │
│ --help                   Show this message and exit.                         │
╰──────────────────────────────────────────────────────────────────────────────╯


</CodeBlock>


</TabItem>
<TabItem value="federation" label="federation">

<CodeBlock language="text" title="CLI Help">
                                                                                
 Usage: vantage cluster federation [OPTIONS] COMMAND         
                                                      [ARGS]...                 
                                                                                
 Manage Vantage compute federations for distributed workloads.                  
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ create   Create a new Vantage federation.                                    │
│ delete   Delete a Vantage federation.                                        │
│ get      Get details of a specific Vantage federation.                       │
│ list     List all Vantage federations.                                       │
│ update   Update a Vantage federation.                                        │
╰──────────────────────────────────────────────────────────────────────────────╯


</CodeBlock>


</TabItem>
</Tabs>

## License Management

<Tabs>
<TabItem value="license" label="🔹 license">

<CodeBlock language="text" title="CLI Help">
                                                                                
 Usage: vantage license [OPTIONS] COMMAND [ARGS]...          
                                                                                
 Manage software licenses, license servers, and licensing configurations.       
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ server          Manage license servers for software licensing and            │
│                 compliance.                                                  │
│ product         Manage license products and software licensing definitions.  │
│ configuration   Manage license configurations and policy settings.           │
│ deployment      Manage license deployments for software distribution and     │
│                 activation.                                                  │
╰──────────────────────────────────────────────────────────────────────────────╯


</CodeBlock>

</TabItem>
<TabItem value="server" label="server">

<CodeBlock language="text" title="CLI Help">
                                                                                
 Usage: vantage license server [OPTIONS] COMMAND [ARGS]...   
                                                                                
 Manage license servers for software licensing and compliance.                  
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ create   Create a new license server.                                        │
│ delete   Delete a license server.                                            │
│ get      Get details of a specific license server.                           │
│ list     List all license servers.                                           │
│ update   Update an existing license server.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯


</CodeBlock>


</TabItem>
<TabItem value="product" label="product">

<CodeBlock language="text" title="CLI Help">
                                                                                
 Usage: vantage license product [OPTIONS] COMMAND [ARGS]...  
                                                                                
 Manage license products and software licensing definitions.                    
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ create   Create a new license product.                                       │
│ delete   Delete a license product.                                           │
│ get      Get details of a specific license product.                          │
│ list     List all license products.                                          │
│ update   Update an existing license product.                                 │
╰──────────────────────────────────────────────────────────────────────────────╯


</CodeBlock>


</TabItem>
<TabItem value="configuration" label="configuration">

<CodeBlock language="text" title="CLI Help">
                                                                                
 Usage: vantage license configuration [OPTIONS] COMMAND      
                                                         [ARGS]...              
                                                                                
 Manage license configurations and policy settings.                             
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ create   Create a new license configuration.                                 │
│ delete   Delete a license configuration.                                     │
│ get      Get details of a specific license configuration.                    │
│ list     List all license configurations.                                    │
│ update   Update an existing license configuration.                           │
╰──────────────────────────────────────────────────────────────────────────────╯


</CodeBlock>


</TabItem>
<TabItem value="deployment" label="deployment">

<CodeBlock language="text" title="CLI Help">
                                                                                
 Usage: vantage license deployment [OPTIONS] COMMAND         
                                                      [ARGS]...                 
                                                                                
 Manage license deployments for software distribution and activation.           
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ create   Create a new license deployment.                                    │
│ delete   Delete a license deployment.                                        │
│ get      Get details of a specific license deployment.                       │
│ list     List all license deployments.                                       │
│ update   Update a license deployment.                                        │
╰──────────────────────────────────────────────────────────────────────────────╯


</CodeBlock>


</TabItem>
</Tabs>

## Network Management

<Tabs>
<TabItem value="network" label="🔹 network">

<CodeBlock language="text" title="CLI Help">
                                                                                
 Usage: vantage network [OPTIONS] COMMAND [ARGS]...          
                                                                                
 Manage virtual networks, subnets, and network configurations for cloud         
 infrastructure.                                                                
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ attach   Attach a network interface to an instance.                          │
│ create   Create a new virtual network.                                       │
│ delete   Delete a virtual network.                                           │
│ detach   Detach a network interface from an instance.                        │
│ get      Get details of a specific virtual network.                          │
│ list     List all virtual networks.                                          │
│ update   Update a virtual network configuration.                             │
╰──────────────────────────────────────────────────────────────────────────────╯


</CodeBlock>

</TabItem>
<TabItem value="attach" label="attach">

<CodeBlock language="text" title="CLI Help">
                                                                                
 Usage: vantage network attach [OPTIONS] NETWORK_ID          
                                                  INSTANCE_ID                   
                                                                                
 Attach a network interface to an instance.                                     
                                                                                
╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    network_id       TEXT  ID of the network to attach [required]           │
│ *    instance_id      TEXT  ID of the instance to attach network to          │
│                             [required]                                       │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --subnet-id         -s      TEXT  Specific subnet ID to attach               │
│ --assign-public-ip                Assign a public IP address                 │
│ --json              -j            Output in JSON format                      │
│ --verbose           -v            Enable verbose terminal output             │
│ --profile           -p      TEXT  Profile name to use [default: default]     │
│ --help                            Show this message and exit.                │
╰──────────────────────────────────────────────────────────────────────────────╯


</CodeBlock>


</TabItem>
<TabItem value="create" label="create">

<CodeBlock language="text" title="CLI Help">
                                                                                
 Usage: vantage network create [OPTIONS] NAME                
                                                                                
 Create a new virtual network.                                                  
                                                                                
╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    name      TEXT  Name of the network to create [required]                │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --cidr         -c      TEXT  CIDR block for the network                      │
│                              [default: 10.0.0.0/16]                          │
│ --region       -r      TEXT  Region for the network                          │
│ --enable-dns                 Enable DNS resolution [default: True]           │
│ --description  -d      TEXT  Description of the network                      │
│ --json         -j            Output in JSON format                           │
│ --verbose      -v            Enable verbose terminal output                  │
│ --profile      -p      TEXT  Profile name to use [default: default]          │
│ --help                       Show this message and exit.                     │
╰──────────────────────────────────────────────────────────────────────────────╯


</CodeBlock>


</TabItem>
<TabItem value="delete" label="delete">

<CodeBlock language="text" title="CLI Help">
                                                                                
 Usage: vantage network delete [OPTIONS] NETWORK_ID          
                                                                                
 Delete a virtual network.                                                      
                                                                                
╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    network_id      TEXT  ID of the network to delete [required]            │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --force    -f            Skip confirmation prompt                            │
│ --json     -j            Output in JSON format                               │
│ --verbose  -v            Enable verbose terminal output                      │
│ --profile  -p      TEXT  Profile name to use [default: default]              │
│ --help                   Show this message and exit.                         │
╰──────────────────────────────────────────────────────────────────────────────╯


</CodeBlock>


</TabItem>
<TabItem value="detach" label="detach">

<CodeBlock language="text" title="CLI Help">
                                                                                
 Usage: vantage network detach [OPTIONS] NETWORK_ID          
                                                  INSTANCE_ID                   
                                                                                
 Detach a network interface from an instance.                                   
                                                                                
╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    network_id       TEXT  ID of the network to detach [required]           │
│ *    instance_id      TEXT  ID of the instance to detach network from        │
│                             [required]                                       │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --force    -f            Force detachment without graceful shutdown          │
│ --json     -j            Output in JSON format                               │
│ --verbose  -v            Enable verbose terminal output                      │
│ --profile  -p      TEXT  Profile name to use [default: default]              │
│ --help                   Show this message and exit.                         │
╰──────────────────────────────────────────────────────────────────────────────╯


</CodeBlock>


</TabItem>
<TabItem value="get" label="get">

<CodeBlock language="text" title="CLI Help">
                                                                                
 Usage: vantage network get [OPTIONS] NETWORK_ID             
                                                                                
 Get details of a specific virtual network.                                     
                                                                                
╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    network_id      TEXT  ID of the network to retrieve [required]          │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --json     -j            Output in JSON format                               │
│ --verbose  -v            Enable verbose terminal output                      │
│ --profile  -p      TEXT  Profile name to use [default: default]              │
│ --help                   Show this message and exit.                         │
╰──────────────────────────────────────────────────────────────────────────────╯


</CodeBlock>


</TabItem>
<TabItem value="list" label="list">

<CodeBlock language="text" title="CLI Help">
                                                                                
 Usage: vantage network list [OPTIONS]                       
                                                                                
 List all virtual networks.                                                     
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --region   -r      TEXT     Filter by region                                 │
│ --status   -s      TEXT     Filter by status                                 │
│ --limit    -l      INTEGER  Maximum number of networks to return             │
│                             [default: 10]                                    │
│ --json     -j               Output in JSON format                            │
│ --verbose  -v               Enable verbose terminal output                   │
│ --profile  -p      TEXT     Profile name to use [default: default]           │
│ --help                      Show this message and exit.                      │
╰──────────────────────────────────────────────────────────────────────────────╯


</CodeBlock>


</TabItem>
<TabItem value="update" label="update">

<CodeBlock language="text" title="CLI Help">
                                                                                
 Usage: vantage network update [OPTIONS] NETWORK_ID          
                                                                                
 Update a virtual network configuration.                                        
                                                                                
╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    network_id      TEXT  ID of the network to update [required]            │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --name         -n                   TEXT  New name for the network           │
│ --description  -d                   TEXT  New description                    │
│ --enable-dns       --disable-dns          Enable or disable DNS resolution   │
│ --json         -j                         Output in JSON format              │
│ --verbose      -v                         Enable verbose terminal output     │
│ --profile      -p                   TEXT  Profile name to use                │
│                                           [default: default]                 │
│ --help                                    Show this message and exit.        │
╰──────────────────────────────────────────────────────────────────────────────╯


</CodeBlock>


</TabItem>
</Tabs>

## Notebook Management

<Tabs>
<TabItem value="notebook" label="🔹 notebook">

<CodeBlock language="text" title="CLI Help">
                                                                                
 Usage: vantage notebook [OPTIONS] COMMAND [ARGS]...         
                                                                                
 Manage Jupyter notebooks and computational notebooks for data science and      
 research.                                                                      
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ create   Create a new Jupyter notebook server.                               │
│ delete   Delete notebook server.                                             │
│ get      Get notebook server details.                                        │
│ list     List notebook servers.                                              │
│ update   Update a Jupyter notebook configuration.                            │
╰──────────────────────────────────────────────────────────────────────────────╯


</CodeBlock>

</TabItem>
<TabItem value="create" label="create">

<CodeBlock language="text" title="CLI Help">
                                                                                
 Usage: vantage notebook create [OPTIONS] NAME               
                                                                                
 Create a new Jupyter notebook server.                                          
                                                                                
╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    name      TEXT  Name of the notebook server [required]                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ *  --cluster    -c      TEXT     Name of the cluster [required]              │
│ *  --partition          TEXT     Name of the partition [required]            │
│    --cpu                INTEGER  Number of CPU cores                         │
│    --memory             FLOAT    Memory in MB                                │
│    --gpus               INTEGER  Number of GPUs                              │
│    --json       -j               Output in JSON format                       │
│    --verbose    -v               Enable verbose terminal output              │
│    --profile    -p      TEXT     Profile name to use [default: default]      │
│    --help                        Show this message and exit.                 │
╰──────────────────────────────────────────────────────────────────────────────╯


</CodeBlock>


</TabItem>
<TabItem value="delete" label="delete">

<CodeBlock language="text" title="CLI Help">
                                                                                
 Usage: vantage notebook delete [OPTIONS] NAME               
                                                                                
 Delete notebook server.                                                        
                                                                                
╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    name      TEXT  Notebook server name [required]                         │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --cluster  -c      TEXT  Cluster name                                        │
│ --force    -f            Force deletion without confirmation                 │
│ --json     -j            Output in JSON format                               │
│ --verbose  -v            Enable verbose terminal output                      │
│ --profile  -p      TEXT  Profile name to use [default: default]              │
│ --help                   Show this message and exit.                         │
╰──────────────────────────────────────────────────────────────────────────────╯


</CodeBlock>


</TabItem>
<TabItem value="get" label="get">

<CodeBlock language="text" title="CLI Help">
                                                                                
 Usage: vantage notebook get [OPTIONS] NAME                  
                                                                                
 Get notebook server details.                                                   
                                                                                
╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    name      TEXT  Notebook server name [required]                         │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --json     -j            Output in JSON format                               │
│ --verbose  -v            Enable verbose terminal output                      │
│ --profile  -p      TEXT  Profile name to use [default: default]              │
│ --help                   Show this message and exit.                         │
╰──────────────────────────────────────────────────────────────────────────────╯


</CodeBlock>


</TabItem>
<TabItem value="list" label="list">

<CodeBlock language="text" title="CLI Help">
                                                                                
 Usage: vantage notebook list [OPTIONS]                      
                                                                                
 List notebook servers.                                                         
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --cluster  -c      TEXT     Filter by cluster name                           │
│ --status   -s      TEXT     Filter by notebook status                        │
│ --kernel   -k      TEXT     Filter by kernel type                            │
│ --limit    -l      INTEGER  Maximum number of notebooks to return            │
│ --json     -j               Output in JSON format                            │
│ --verbose  -v               Enable verbose terminal output                   │
│ --profile  -p      TEXT     Profile name to use [default: default]           │
│ --help                      Show this message and exit.                      │
╰──────────────────────────────────────────────────────────────────────────────╯


</CodeBlock>


</TabItem>
<TabItem value="update" label="update">

<CodeBlock language="text" title="CLI Help">
                                                                                
 Usage: vantage notebook update [OPTIONS] NOTEBOOK_ID        
                                                                                
 Update a Jupyter notebook configuration.                                       
                                                                                
╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    notebook_id      TEXT  ID of the notebook to update [required]          │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --name         -n      TEXT  New name for the notebook                       │
│ --description  -d      TEXT  New description                                 │
│ --kernel       -k      TEXT  New kernel type                                 │
│ --json         -j            Output in JSON format                           │
│ --verbose      -v            Enable verbose terminal output                  │
│ --profile      -p      TEXT  Profile name to use [default: default]          │
│ --help                       Show this message and exit.                     │
╰──────────────────────────────────────────────────────────────────────────────╯


</CodeBlock>


</TabItem>
</Tabs>

## Profile Management

<Tabs>
<TabItem value="profile" label="🔹 profile">

<CodeBlock language="text" title="CLI Help">
                                                                                
 Usage: vantage profile [OPTIONS] COMMAND [ARGS]...          
                                                                                
 Manage Vantage CLI profiles to work with different environments and            
 configurations.                                                                
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ create   Create a new Vantage CLI profile.                                   │
│ delete   Delete a Vantage CLI profile.                                       │
│ get      Get details of a specific Vantage CLI profile.                      │
│ list     List all Vantage CLI profiles.                                      │
│ use      Activate a profile for use in the current session.                  │
╰──────────────────────────────────────────────────────────────────────────────╯


</CodeBlock>

</TabItem>
<TabItem value="create" label="create">

<CodeBlock language="text" title="CLI Help">
                                                                                
 Usage: vantage profile create [OPTIONS] COMMAND_START_TIME  
                                                  PROFILE_NAME                  
                                                                                
 Create a new Vantage CLI profile.                                              
                                                                                
╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    command_start_time      FLOAT  [required]                               │
│ *    profile_name            TEXT   Name of the profile to create [required] │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --api-url                TEXT     API base URL                               │
│                                   [default: https://apis.vantagecompute.ai]  │
│ --tunnel-url             TEXT     Tunnel API URL                             │
│                                   [default:                                  │
│                                   https://tunnel.vantagecompute.ai]          │
│ --oidc-url               TEXT     OIDC base URL                              │
│                                   [default: https://auth.vantagecompute.ai]  │
│ --client-id              TEXT     OIDC client ID [default: default]          │
│ --max-poll-time          INTEGER  OIDC max poll time in seconds              │
│                                   [default: 300]                             │
│ --force          -f               Overwrite existing profile                 │
│ --activate                        Activate this profile after creation       │
│ --json           -j               Output in JSON format                      │
│ --verbose        -v               Enable verbose terminal output             │
│ --help                            Show this message and exit.                │
╰──────────────────────────────────────────────────────────────────────────────╯


</CodeBlock>


</TabItem>
<TabItem value="delete" label="delete">

<CodeBlock language="text" title="CLI Help">
                                                                                
 Usage: vantage profile delete [OPTIONS] PROFILE_NAME        
                                                                                
 Delete a Vantage CLI profile.                                                  
                                                                                
╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    profile_name      TEXT  Name of the profile to delete [required]        │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --force    -f        Skip confirmation prompt                                │
│ --json     -j        Output in JSON format                                   │
│ --verbose  -v        Enable verbose terminal output                          │
│ --help               Show this message and exit.                             │
╰──────────────────────────────────────────────────────────────────────────────╯


</CodeBlock>


</TabItem>
<TabItem value="get" label="get">

<CodeBlock language="text" title="CLI Help">
                                                                                
 Usage: vantage profile get [OPTIONS] PROFILE_NAME           
                                                                                
 Get details of a specific Vantage CLI profile.                                 
                                                                                
╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    profile_name      TEXT  Name of the profile to get details for          │
│                              [required]                                      │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --json     -j        Output in JSON format                                   │
│ --verbose  -v        Enable verbose terminal output                          │
│ --help               Show this message and exit.                             │
╰──────────────────────────────────────────────────────────────────────────────╯


</CodeBlock>


</TabItem>
<TabItem value="list" label="list">

<CodeBlock language="text" title="CLI Help">
                                                                                
 Usage: vantage profile list [OPTIONS]                       
                                                                                
 List all Vantage CLI profiles.                                                 
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --json     -j        Output in JSON format                                   │
│ --verbose  -v        Enable verbose terminal output                          │
│ --help               Show this message and exit.                             │
╰──────────────────────────────────────────────────────────────────────────────╯


</CodeBlock>


</TabItem>
<TabItem value="use" label="use">

<CodeBlock language="text" title="CLI Help">
                                                                                
 Usage: vantage profile use [OPTIONS] PROFILE_NAME           
                                                                                
 Activate a profile for use in the current session.                             
                                                                                
╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    profile_name      TEXT  Name of the profile to activate [required]      │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --json     -j        Output in JSON format                                   │
│ --verbose  -v        Enable verbose terminal output                          │
│ --help               Show this message and exit.                             │
╰──────────────────────────────────────────────────────────────────────────────╯


</CodeBlock>


</TabItem>
</Tabs>

## Storage Management

<Tabs>
<TabItem value="storage" label="🔹 storage">

<CodeBlock language="text" title="CLI Help">
                                                                                
 Usage: vantage storage [OPTIONS] COMMAND [ARGS]...          
                                                                                
 Manage storage volumes, disks, and storage configurations for cloud            
 infrastructure.                                                                
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ attach   Attach a storage volume to an instance.                             │
│ create   Create a new storage volume.                                        │
│ delete   Delete a storage volume.                                            │
│ detach   Detach a storage volume from an instance.                           │
│ get      Get details of a specific storage volume.                           │
│ list     List all storage volumes.                                           │
│ update   Update a storage volume configuration.                              │
╰──────────────────────────────────────────────────────────────────────────────╯


</CodeBlock>

</TabItem>
<TabItem value="attach" label="attach">

<CodeBlock language="text" title="CLI Help">
                                                                                
 Usage: vantage storage attach [OPTIONS] STORAGE_ID          
                                                  INSTANCE_ID                   
                                                                                
 Attach a storage volume to an instance.                                        
                                                                                
╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    storage_id       TEXT  ID of the storage volume to attach [required]    │
│ *    instance_id      TEXT  ID of the instance to attach storage to          │
│                             [required]                                       │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --mount-point  -m      TEXT  Mount point for the storage [default: /data]    │
│ --read-only    -r            Attach storage in read-only mode                │
│ --json         -j            Output in JSON format                           │
│ --verbose      -v            Enable verbose terminal output                  │
│ --profile      -p      TEXT  Profile name to use [default: default]          │
│ --help                       Show this message and exit.                     │
╰──────────────────────────────────────────────────────────────────────────────╯


</CodeBlock>


</TabItem>
<TabItem value="create" label="create">

<CodeBlock language="text" title="CLI Help">
                                                                                
 Usage: vantage storage create [OPTIONS] NAME                
                                                                                
 Create a new storage volume.                                                   
                                                                                
╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    name      TEXT  Name of the storage volume to create [required]         │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --size         -s      INTEGER  Size of the storage volume in GB             │
│                                 [default: 10]                                │
│ --type         -t      TEXT     Storage type (ssd, hdd, nvme) [default: ssd] │
│ --zone         -z      TEXT     Availability zone for the storage            │
│ --description  -d      TEXT     Description of the storage volume            │
│ --json         -j               Output in JSON format                        │
│ --verbose      -v               Enable verbose terminal output               │
│ --profile      -p      TEXT     Profile name to use [default: default]       │
│ --help                          Show this message and exit.                  │
╰──────────────────────────────────────────────────────────────────────────────╯


</CodeBlock>


</TabItem>
<TabItem value="delete" label="delete">

<CodeBlock language="text" title="CLI Help">
                                                                                
 Usage: vantage storage delete [OPTIONS] STORAGE_ID          
                                                                                
 Delete a storage volume.                                                       
                                                                                
╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    storage_id      TEXT  ID of the storage volume to delete [required]     │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --force    -f            Skip confirmation prompt                            │
│ --json     -j            Output in JSON format                               │
│ --verbose  -v            Enable verbose terminal output                      │
│ --profile  -p      TEXT  Profile name to use [default: default]              │
│ --help                   Show this message and exit.                         │
╰──────────────────────────────────────────────────────────────────────────────╯


</CodeBlock>


</TabItem>
<TabItem value="detach" label="detach">

<CodeBlock language="text" title="CLI Help">
                                                                                
 Usage: vantage storage detach [OPTIONS] STORAGE_ID          
                                                                                
 Detach a storage volume from an instance.                                      
                                                                                
╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    storage_id      TEXT  ID of the storage volume to detach [required]     │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --force    -f            Force detachment without graceful unmounting        │
│ --json     -j            Output in JSON format                               │
│ --verbose  -v            Enable verbose terminal output                      │
│ --profile  -p      TEXT  Profile name to use [default: default]              │
│ --help                   Show this message and exit.                         │
╰──────────────────────────────────────────────────────────────────────────────╯


</CodeBlock>


</TabItem>
<TabItem value="get" label="get">

<CodeBlock language="text" title="CLI Help">
                                                                                
 Usage: vantage storage get [OPTIONS] STORAGE_ID             
                                                                                
 Get details of a specific storage volume.                                      
                                                                                
╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    storage_id      TEXT  ID of the storage volume to retrieve [required]   │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --json     -j            Output in JSON format                               │
│ --verbose  -v            Enable verbose terminal output                      │
│ --profile  -p      TEXT  Profile name to use [default: default]              │
│ --help                   Show this message and exit.                         │
╰──────────────────────────────────────────────────────────────────────────────╯


</CodeBlock>


</TabItem>
<TabItem value="list" label="list">

<CodeBlock language="text" title="CLI Help">
                                                                                
 Usage: vantage storage list [OPTIONS]                       
                                                                                
 List all storage volumes.                                                      
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --zone     -z      TEXT     Filter by availability zone                      │
│ --type     -t      TEXT     Filter by storage type                           │
│ --status   -s      TEXT     Filter by status                                 │
│ --limit    -l      INTEGER  Maximum number of storage volumes to return      │
│                             [default: 10]                                    │
│ --json     -j               Output in JSON format                            │
│ --verbose  -v               Enable verbose terminal output                   │
│ --profile  -p      TEXT     Profile name to use [default: default]           │
│ --help                      Show this message and exit.                      │
╰──────────────────────────────────────────────────────────────────────────────╯


</CodeBlock>


</TabItem>
<TabItem value="update" label="update">

<CodeBlock language="text" title="CLI Help">
                                                                                
 Usage: vantage storage update [OPTIONS] STORAGE_ID          
                                                                                
 Update a storage volume configuration.                                         
                                                                                
╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    storage_id      TEXT  ID of the storage volume to update [required]     │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --name         -n      TEXT     New name for the storage volume              │
│ --size         -s      INTEGER  New size in GB (expansion only)              │
│ --description  -d      TEXT     New description                              │
│ --iops                 INTEGER  New IOPS setting                             │
│ --json         -j               Output in JSON format                        │
│ --verbose      -v               Enable verbose terminal output               │
│ --profile      -p      TEXT     Profile name to use [default: default]       │
│ --help                          Show this message and exit.                  │
╰──────────────────────────────────────────────────────────────────────────────╯


</CodeBlock>


</TabItem>
</Tabs>

## Deployment Management

<Tabs>
<TabItem value="deployment" label="🔹 deployment">

<CodeBlock language="text" title="CLI Help">
                                                                                
 Usage: vantage deployment [OPTIONS] COMMAND [ARGS]...       
                                                                                
 Create and manage application deployments on Vantage compute clusters.         
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ list                            List all active deployments from             │
│                                 ~/.vantage-cli/deployments.yaml.             │
│ slurm-microk8s-localhost        Commands for slurm-microk8s-localhost.       │
│ slurm-juju-localhost            Commands for slurm-juju-localhost.           │
│ slurm-multipass-localhost       Commands for slurm-multipass-localhost.      │
│ jupyterhub-microk8s-localhost   Commands for jupyterhub-microk8s-localhost.  │
╰──────────────────────────────────────────────────────────────────────────────╯


</CodeBlock>

</TabItem>
<TabItem value="list" label="list">

<CodeBlock language="text" title="CLI Help">
                                                                                
 Usage: vantage deployment list [OPTIONS]                    
                                                                                
 List all active deployments from ~/.vantage-cli/deployments.yaml.              
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --cloud            TEXT  Filter deployments by cloud type (e.g., localhost,  │
│                          aws, gcp)                                           │
│ --json     -j            Output in JSON format                               │
│ --verbose  -v            Enable verbose terminal output                      │
│ --profile  -p      TEXT  Profile name to use [default: default]              │
│ --help                   Show this message and exit.                         │
╰──────────────────────────────────────────────────────────────────────────────╯


</CodeBlock>


</TabItem>
</Tabs>

## Configuration Management

<Tabs>
<TabItem value="config" label="🔹 config">

<CodeBlock language="text" title="CLI Help">
                                                                                
 Usage: vantage config [OPTIONS] COMMAND [ARGS]...           
                                                                                
 Manage Vantage CLI configuration and settings.                                 
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ clear   Clear all user tokens and configuration.                             │
╰──────────────────────────────────────────────────────────────────────────────╯


</CodeBlock>

</TabItem>
<TabItem value="clear" label="clear">

<CodeBlock language="text" title="CLI Help">
                                                                                
 Usage: vantage config clear [OPTIONS]                       
                                                                                
 Clear all user tokens and configuration.                                       
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --force    -f            Skip confirmation prompt                            │
│ --json     -j            Output in JSON format                               │
│ --verbose  -v            Enable verbose terminal output                      │
│ --profile  -p      TEXT  Profile name to use [default: default]              │
│ --help                   Show this message and exit.                         │
╰──────────────────────────────────────────────────────────────────────────────╯


</CodeBlock>


</TabItem>
</Tabs>
