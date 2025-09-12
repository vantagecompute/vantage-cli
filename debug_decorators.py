#!/usr/bin/env python3
"""Debug script to understand how the decorators work."""

import inspect
import typer
from vantage_cli.decorators import vantage_command, JsonOption

app = typer.Typer()

# Test the decorator manually
def test_func(ctx: typer.Context):
    return "test"

print("Original function signature:")
print(inspect.signature(test_func))

# Apply the decorator manually to see what happens
decorator = vantage_command(app, "test")
wrapped = decorator(test_func)

print("\nAfter applying vantage_command:")
print(f"wrapped is: {wrapped}")
print(f"wrapped type: {type(wrapped)}")
print(f"wrapped signature: {inspect.signature(wrapped)}")

print(f"\nRegistered commands: {len(app.registered_commands)}")
if app.registered_commands:
    cmd = app.registered_commands[0]
    print(f"Command name: {cmd.name}")
    print(f"Command callback: {cmd.callback}")
    print(f"Command callback type: {type(cmd.callback)}")
    if cmd.callback:
        print(f"Command callback signature: {inspect.signature(cmd.callback)}")

# Let's also test what the wrapper function looks like in isolation
import functools

def manual_wrapper(func):
    @functools.wraps(func)
    def wrapper(ctx: typer.Context, *args, json_output: JsonOption = False, **kwargs):
        print(f"Wrapper called with json_output={json_output}")
        return func(ctx, *args, **kwargs)
    return wrapper

wrapped_manual = manual_wrapper(test_func)
print(f"\nManual wrapper signature: {inspect.signature(wrapped_manual)}")