"""Clouds alias command - maps to 'vantage cloud list'."""

import typer

from vantage_cli.commands.cloud.list import list_command


def clouds_command(
    ctx: typer.Context,
) -> None:
    """List all configured cloud providers.

    This is an alias for 'vantage cloud list'.
    """
    list_command(ctx)


def main():
    """Entry point for direct execution."""
    # This would typically be called through the CLI
    pass


if __name__ == "__main__":
    main()
