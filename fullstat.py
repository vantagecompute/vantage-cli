# Copyright 2023 Canonical Ltd.
# Licensed under the Apache V2, see LICENCE file for details.

"""This example demonstrates how to obtain a formatted full status
description. For a similar solution using the FullStatus object
check examples/fullstatus.py
"""

import asyncio
import logging
import sys
import tempfile
from logging import getLogger

from juju.model import Model
from juju.status import formatted_status

LOG = getLogger(__name__)
logging.basicConfig(stream=sys.stdout, level=logging.INFO)


async def main():
    model = Model()
    await model.connect_current()

    #await asyncio.sleep(10)
    for _ in range(10):

        status = await model.get_status()

        print("Applications:", list(status.applications.keys()))
        print("Machines:", list(status.machines.keys()))
        print("Relations:", status.relations)
        await asyncio.sleep(1)

    await model.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
