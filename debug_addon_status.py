#!/usr/bin/env python3

import subprocess
import yaml

def debug_addon_status():
    try:
        # Get MicroK8s status in YAML format
        result = subprocess.run(
            ["microk8s", "status", "--format", "yaml"],
            capture_output=True,
            text=True,
            check=True
        )
        
        print("=== Raw YAML Output ===")
        print(result.stdout[:500] + "..." if len(result.stdout) > 500 else result.stdout)
        print("\n=== Parsed Data ===")
        
        status_data = yaml.safe_load(result.stdout)
        print(f"MicroK8s running: {status_data.get('microk8s', {}).get('running', False)}")
        
        # Get enabled addons
        enabled_addons = set()
        addons_list = status_data.get("addons", [])
        print(f"\nTotal addons found: {len(addons_list)}")
        
        for addon in addons_list:
            addon_name = addon.get("name")
            addon_status = addon.get("status")
            print(f"  {addon_name}: {addon_status}")
            if addon_status == "enabled":
                enabled_addons.add(addon_name)
        
        print(f"\nEnabled addons: {sorted(enabled_addons)}")
        
        required_addons = ["dns", "hostpath-storage", "metallb", "helm3"]
        print(f"Required addons: {required_addons}")
        
        for addon in required_addons:
            status = "✅ ENABLED" if addon in enabled_addons else "❌ MISSING"
            print(f"  {addon}: {status}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    debug_addon_status()