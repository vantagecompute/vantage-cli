#!/usr/bin/env python3

import subprocess

def debug_namespace_check():
    try:
        print("=== Testing namespace check ===")
        
        # Test the exact command
        result = subprocess.run(
            ["microk8s.kubectl", "get", "namespaces", "-o", "name"],
            capture_output=True,
            text=True,
            check=True
        )
        
        print(f"Command output:\n{result.stdout}")
        print(f"Return code: {result.returncode}")
        
        # Parse namespace names
        existing_namespaces = set()
        for line in result.stdout.strip().split('\n'):
            print(f"Processing line: '{line}'")
            if line.startswith('namespace/'):
                namespace_name = line.replace('namespace/', '')
                existing_namespaces.add(namespace_name)
                print(f"  Added namespace: {namespace_name}")
        
        print(f"\nFound namespaces: {sorted(existing_namespaces)}")
        
        # Check for SLURM-related namespaces
        slurm_namespaces = {'slinky', 'slurm'}
        found_namespaces = slurm_namespaces.intersection(existing_namespaces)
        
        print(f"SLURM namespaces we're looking for: {slurm_namespaces}")
        print(f"Found SLURM namespaces: {found_namespaces}")
        
        if found_namespaces:
            print("❌ DEPLOYMENT EXISTS!")
            return True
        else:
            print("✅ No deployment found")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed: {e}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    debug_namespace_check()