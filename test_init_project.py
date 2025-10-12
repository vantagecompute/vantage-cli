#!/usr/bin/env python3
"""Test script for init_project_and_head_node function."""

import asyncio
import os
import sys

# Mock context object for testing
class MockObj:
    def __init__(self, cudo_sdk):
        self.cudo_sdk = cudo_sdk

class MockContext:
    def __init__(self, cudo_sdk):
        self.obj = MockObj(cudo_sdk)

async def test_init_project():
    """Test the init_project_and_head_node function."""
    import json
    import yaml
    from pathlib import Path
    from vantage_cli.clouds.cudo_compute.sdk import CudoComputeSDK
    from vantage_cli.clouds.cudo_compute.apps.slurm_metal.utils import init_project_and_head_node
    
    # Get API key from environment or credentials file
    api_key = os.getenv("CUDO_COMPUTE_API_KEY")
    
    if not api_key:
        # Try loading from credentials.yaml
        creds_file = Path.home() / ".vantage-cli" / "credentials.yaml"
        if creds_file.exists():
            try:
                creds = yaml.safe_load(creds_file.read_text())
                # Find the default cudo-compute credential
                for cred_id, cred_data in creds.get("credentials", {}).items():
                    if cred_data.get("cloud_id") == "cudo-compute" and cred_data.get("default"):
                        api_key = cred_data.get("credentials_data", {}).get("api_key")
                        break
            except Exception as e:
                print(f"Error loading credentials: {e}")
    
    if not api_key:
        print("Error: No Cudo Compute API key found")
        print("Please set CUDO_COMPUTE_API_KEY environment variable")
        print("Or ensure a default cudo-compute credential exists in ~/.vantage-cli/credentials.yaml")
        sys.exit(1)
    
    # Create SDK instance
    sdk = CudoComputeSDK(api_key=api_key)
    
    # Create mock context
    ctx = MockContext(sdk)
    
    # Test VM specs
    vm_specs = [{
        "name": "test-vm-init",
        "machine_type": "standard",
        "vcpus": 2,
        "memory_gib": 4,
        "gpus": 0,
        "boot_disk_size_gib": 20,
    }]
    
    print("🚀 Starting project and VM creation test...")
    print(f"Project name: test-project-{int(asyncio.get_event_loop().time())}")
    
    try:
        vm_id = await init_project_and_head_node(
            ctx=ctx,
            project_name=f"test-project-{int(asyncio.get_event_loop().time())}",
            vm_specs=vm_specs,
        )
        print(f"\n✅ Success! VM created with ID: {vm_id}")
        print("\nTest completed successfully!")
        print("\n⚠️  Remember to clean up the test resources:")
        print("   1. Delete the VM")
        print("   2. Delete the security group")
        print("   3. Delete the network")
        print("   4. Delete the project")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        # Try to get more details if it's an HTTP error
        if hasattr(e, 'response') and hasattr(e.response, 'text'):
            print(f"Response details: {e.response.text}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_init_project())
