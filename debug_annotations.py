#!/usr/bin/env python3
"""Debug script to check if JsonOption annotation is the issue."""

import inspect
import typer
import functools
from typing_extensions import Annotated

JsonOption = Annotated[bool, typer.Option("--json", "-j", help="Output in JSON format")]

def test_wrapper1(ctx: typer.Context, json_output: bool = False):
    """Wrapper with plain bool type."""
    return "test"

def test_wrapper2(ctx: typer.Context, json_output: JsonOption = False):
    """Wrapper with JsonOption type.""" 
    return "test"

print("test_wrapper1 signature (plain bool):")
print(inspect.signature(test_wrapper1))

print("\ntest_wrapper2 signature (JsonOption):")
print(inspect.signature(test_wrapper2))

# Test parameter inspection
sig1 = inspect.signature(test_wrapper1)
sig2 = inspect.signature(test_wrapper2)

print(f"\ntest_wrapper1 parameters: {list(sig1.parameters.keys())}")
print(f"test_wrapper2 parameters: {list(sig2.parameters.keys())}")

print(f"\njson_output param in wrapper1: {'json_output' in sig1.parameters}")
print(f"json_output param in wrapper2: {'json_output' in sig2.parameters}")

if 'json_output' in sig2.parameters:
    param = sig2.parameters['json_output']
    print(f"json_output annotation: {param.annotation}")
    print(f"json_output default: {param.default}")