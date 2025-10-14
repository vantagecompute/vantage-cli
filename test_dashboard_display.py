#!/usr/bin/env python3
"""Test script to debug dashboard display issues"""

from vantage_cli.dashboard import DashboardApp, DashboardConfig

# Create minimal config
config = DashboardConfig(
    title="Test Dashboard",
    enable_logs=False,
    enable_stats=False,
    enable_controls=False,
    enable_clusters=False
)

# Run app
app = DashboardApp(config=config)
app.run()
