#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from vantage_cli.exceptions import Abort

def test_addon_check():
    try:
        from vantage_cli.apps.slurm_microk8s_localhost.utils import check_microk8s_addons
        print("Testing addon checking...")
        check_microk8s_addons()
        print("✅ All required addons are enabled!")
        return True
    except Abort as e:
        print(f"❌ Addon check failed:")
        print(f"Subject: {e.subject}")
        print(f"Message: {e.message}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = test_addon_check()
    sys.exit(0 if success else 1)