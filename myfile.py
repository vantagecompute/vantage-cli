#!/usr/bin/env python3
import asyncio
from cudo_compute_sdk import CudoComputeSDK

async def main():
    sdk = CudoComputeSDK(api_key="your-api-key-here")
    try:
        projects = await sdk.list_projects()
        for project in projects:
            vms = await sdk.list_vms(project_id=project.id)
            print(f"Number of VMs: {len(vms)} - In project: {project.id}")
    finally:
        await sdk.close()

asyncio.run(main())




