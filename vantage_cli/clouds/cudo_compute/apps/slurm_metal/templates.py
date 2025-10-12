"""Templates for Slurm Metal app."""

from textwrap import dedent


INIT_SCRIPT = dedent(
    """#!/bin/bash
    apt-get update
    """
)