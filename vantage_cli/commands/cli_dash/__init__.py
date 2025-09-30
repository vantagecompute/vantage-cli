# Copyright (C) 2025 Vantage Compute Corporation
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, version 3.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# this program. If not, see <https://www.gnu.org/licenses/>.
"""Vantage `cli-dash` command for the Vantage CLI."""
import typer

from vantage_cli.config import attach_settings
from vantage_cli.dashboard import (
    DashboardApp, 
    DashboardConfig, 
    ServiceConfig
)
from vantage_cli.exceptions import handle_abort


def my_custom_cert_handler(worker_id: str) -> dict:
    """Custom handler for certificate management"""
    import time
    time.sleep(0.5)  # Simulate work
    return {"duration": 0.5, "status": "certificates_renewed"}


def my_custom_db_handler(worker_id: str) -> dict:
    """Custom handler for database operations"""
    import time
    time.sleep(1.0)  # Simulate work
    return {"duration": 1.0, "status": "database_migrated"}


@handle_abort
@attach_settings
def cli_dash(
    ctx: typer.Context,
) -> None:
    """Vantage CLI Dashboard - Interactive terminal dashboard."""

    title = "Vantage CLI Dashboard"
    config = DashboardConfig(
        title=title,
        subtitle="Custom Deployment Application Monitor",
        enable_stats=True,
        enable_logs=True,
        enable_controls=True,
        enable_clusters=True,  # Enable cluster management
        refresh_interval=0.5,
    )
    
    # Custom services
    services = [
        ServiceConfig("cert-manager", "https://certs.myapp.com", "🔐"),
        ServiceConfig("database", "https://db.myapp.com", "🗄️"),
        ServiceConfig("api-server", "https://api.myapp.com", "🚀", ["cert-manager", "database"]),
        ServiceConfig("frontend", "https://app.myapp.com", "🌐", ["api-server"]),
        ServiceConfig("monitoring", "https://monitor.myapp.com", "📊", ["api-server"])
    ]
    
    # Custom handlers for specific services
    custom_handlers = {
        "cert-manager": my_custom_cert_handler,
        "database": my_custom_db_handler,
        # Other services will use default dummy handlers
    }
    
    # Custom platform info
    platform_info = {
        "name": "MyApp Platform",
        "cluster_url": "https://console.myapp.com/clusters",
        "notebooks_url": "https://notebooks.myapp.com",
        "docs_url": "https://docs.myapp.com",
        "support_email": "support@myapp.com"
    }
    
    typer.echo(f"🚀 Launching {title}...")
    
    # Create the dashboard app
    app_instance = DashboardApp(
        config=config,
        services=services,
        custom_handlers=custom_handlers,
        platform_info=platform_info,
        ctx=ctx  # Pass the typer context for cluster management
    )
    
    try:
        typer.echo("💡 Use Ctrl+C to quit, or 'q' inside the app")
        # Run the dashboard synchronously since Textual apps are sync
        app_instance.run()
    except KeyboardInterrupt:
        typer.echo("\n👋 Dashboard interrupted by user")
    except Exception as e:
        typer.echo(f"\n💥 Dashboard error: {e}")
        raise typer.Exit(1)