#!/usr/bin/env python3
"""Debug script to test functools.wraps behavior."""

import inspect
import typer
import functools
from typing_extensions import Annotated

JsonOption = Annotated[bool, typer.Option("--json", "-j", help="Output in JSON format")]

def original_func(ctx: typer.Context):
    """Original function."""
    return "original"

print("Original function signature:")
print(inspect.signature(original_func))

# Test wrapper WITHOUT functools.wraps
def wrapper_no_wraps(ctx: typer.Context, json_output: JsonOption = False):
    """Wrapper without functools.wraps."""
    return original_func(ctx)

print(f"\nWrapper without @functools.wraps signature:")
print(inspect.signature(wrapper_no_wraps))

# Test wrapper WITH functools.wraps
@functools.wraps(original_func)
def wrapper_with_wraps(ctx: typer.Context, json_output: JsonOption = False):
    """Wrapper with functools.wraps."""
    return original_func(ctx)

print(f"\nWrapper with @functools.wraps signature:")
print(inspect.signature(wrapper_with_wraps))

print(f"\nWrapper without wraps parameters: {list(inspect.signature(wrapper_no_wraps).parameters.keys())}")
print(f"Wrapper with wraps parameters: {list(inspect.signature(wrapper_with_wraps).parameters.keys())}")

# Check what __wrapped__ attribute contains
if hasattr(wrapper_with_wraps, '__wrapped__'):
    print(f"\n__wrapped__ signature: {inspect.signature(wrapper_with_wraps.__wrapped__)}")
    
# Test manually setting signature
wrapper_manual = lambda ctx, json_output=False: original_func(ctx)
wrapper_manual.__name__ = original_func.__name__
wrapper_manual.__doc__ = original_func.__doc__

print(f"\nManual wrapper (before signature): {inspect.signature(wrapper_manual)}")

# Manually set the signature
from inspect import Parameter, Signature
params = [
    Parameter('ctx', Parameter.POSITIONAL_OR_KEYWORD, annotation=typer.Context),
    Parameter('json_output', Parameter.KEYWORD_ONLY, default=False, annotation=JsonOption)
]
wrapper_manual.__signature__ = Signature(params)

print(f"Manual wrapper (after signature): {inspect.signature(wrapper_manual)}")