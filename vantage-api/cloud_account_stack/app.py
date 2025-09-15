#!/usr/bin/env python3
"""Synthesize the Cloud Account Stack."""
import aws_cdk as cdk

try:
    from cloud_account_stack.cloud_account_stack.stack import CloudAccountStack
except ModuleNotFoundError:
    from cloud_account_stack.stack import CloudAccountStack

app = cdk.App()
cloud_account_stack = CloudAccountStack(
    app, "CloudAccountStack", synthesizer=cdk.DefaultStackSynthesizer(generate_bootstrap_version_rule=False)
)
cdk.Tags.of(app).add("ManagedBy", "Vantage")

if __name__ == "__main__":
    app.synth()
