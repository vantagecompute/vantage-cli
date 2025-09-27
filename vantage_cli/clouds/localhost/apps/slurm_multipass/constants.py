"""SLURM Multipass Localhost Constants."""

from pathlib import Path

APP_NAME = "slurm-multipass-localhost"

CLOUD = "localhost"

SUBSTRATE = "multipass"

MULTIPASS_ARCH = "arm64"

MULTIPASS_CLOUD_IMAGE_URL = "https://vantage-public-assets.s3.us-west-2.amazonaws.com/multipass-singlenode/multipass-singlenode.img"

MULTIPASS_CLOUD_IMAGE_DEST = Path("/tmp/multipass-singlenode.img")

MULTIPASS_CLOUD_IMAGE_LOCAL = (
    Path.home() / "multipass-singlenode" / "build" / "multipass-singlenode.img"
)
