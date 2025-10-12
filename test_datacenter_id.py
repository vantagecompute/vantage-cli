#!/usr/bin/env python3
"""Test get_datacenter_id_from_credentials method."""

from vantage_cli.clouds.cudo_compute.sdk import CudoComputeSDK

# Test the new method
datacenter_id = CudoComputeSDK.get_datacenter_id_from_credentials()

if datacenter_id:
    print(f"✓ Datacenter ID from credentials: {datacenter_id}")
else:
    print("✗ No datacenter_id found in credentials")
    print("  (This is okay if datacenter_id hasn't been added to credentials yet)")
