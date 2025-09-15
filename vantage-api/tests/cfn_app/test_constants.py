"""Test the constants used in the cfn_app module."""
from api.cfn_app import contants


def test_supported_region():
    """Test if the supported regions are the expected ones."""
    ami_mapper = contants.AMI_MAPPER
    regions = [
        "af-south-1",
        "ap-east-1",
        "ap-northeast-1",
        "ap-northeast-2",
        "ap-northeast-3",
        "ap-south-1",
        "ap-south-2",
        "ap-southeast-1",
        "ap-southeast-2",
        "ap-southeast-3",
        "ap-southeast-4",
        "ap-southeast-5",
        "ap-southeast-7",
        "ca-central-1",
        "ca-west-1",
        "eu-central-1",
        "eu-central-2",
        "eu-north-1",
        "eu-south-1",
        "eu-south-2",
        "eu-west-1",
        "eu-west-2",
        "eu-west-3",
        "il-central-1",
        "me-central-1",
        "me-south-1",
        "mx-central-1",
        "sa-east-1",
        "us-east-1",
        "us-east-2",
        "us-west-1",
        "us-west-2",
    ]
    assert list(ami_mapper.get("head").keys()) == regions
    assert list(ami_mapper.get("compute").keys()) == regions
