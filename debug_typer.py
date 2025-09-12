#!/usr/bin/env python3
"""Debug script to understand how typer.command works."""

import inspect
import typer
import functools
from typing_extensions import Annotated

app = typer.Typer()

JsonOption = Annotated[bool, typer.Option("--json", "-j", help="Output in JSON format")]

def original_func(ctx: typer.Context):
    return "original"

print("Original function signature:")
print(inspect.signature(original_func))

# Create a wrapper manually  
@functools.wraps(original_func)
def wrapper(ctx: typer.Context, *args, json_output: JsonOption = False, **kwargs):
    return original_func(ctx, *args, **kwargs)

print(f"\nWrapper signature: {inspect.signature(wrapper)}")

# Test what app.command returns
result = app.command("test")(wrapper)

print(f"\napp.command result: {result}")
print(f"result is wrapper: {result is wrapper}")
print(f"result is original_func: {result is original_func}")
print(f"result signature: {inspect.signature(result)}")

# Check what's registered
print(f"\nRegistered commands: {len(app.registered_commands)}")
if app.registered_commands:
    cmd = app.registered_commands[0]
    print(f"Command callback: {cmd.callback}")
    print(f"Callback is wrapper: {cmd.callback is wrapper}")
    print(f"Callback is result: {cmd.callback is result}")
    print(f"Callback signature: {inspect.signature(cmd.callback)}")