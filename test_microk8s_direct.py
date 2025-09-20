#!/usr/bin/env python3

import subprocess
import yaml

def test_microk8s_status():
    try:
        # Get MicroK8s status in YAML format
        result = subprocess.run(
            ["microk8s", "status", "--format", "yaml"],
            capture_output=True,
            text=True,
            check=True
        )
        status_data = yaml.safe_load(result.stdout)
        print("✅ Successfully got MicroK8s status")
        
        # Check if MicroK8s is running
        if not status_data.get("microk8s", {}).get("running", False):
            print("❌ MicroK8s is not running")
            return False
            
        print("✅ MicroK8s is running")
        
        # Get enabled addons
        enabled_addons = set()
        addons_list = status_data.get("addons", [])
        for addon in addons_list:
            if addon.get("status") == "enabled":
                addon_name = addon.get("name")
                if addon_name:
                    enabled_addons.add(addon_name)
        
        print(f"✅ Enabled addons: {sorted(enabled_addons)}")
        
        required_addons = ["dns", "hostpath-storage", "helm3"]
        missing_addons = []
        
        for addon_name in required_addons:
            if addon_name in enabled_addons:
                print(f"✅ {addon_name}: enabled")
            else:
                print(f"❌ {addon_name}: missing")
                missing_addons.append(addon_name)
        
        if missing_addons:
            print(f"\n❌ Missing required addons: {missing_addons}")
            return False
        else:
            print("\n✅ All required addons are enabled!")
            return True
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to get MicroK8s status: {e}")
        return False
    except yaml.YAMLError as e:
        print(f"❌ Failed to parse MicroK8s status: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = test_microk8s_status()
    exit(0 if success else 1)