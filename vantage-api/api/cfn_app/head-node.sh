#!/bin/bash -x
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -

DEBIAN_FRONTEND=noninteractive apt update
DEBIAN_FRONTEND=noninteractive apt install python3-pip nodejs -y
pip3 install https://s3.amazonaws.com/cloudformation-examples/aws-cfn-bootstrap-py3-latest.tar.gz
pip3 install boto3
npm install -g configurable-http-proxy@4.6.3
/usr/local/bin/cfn-init --stack @stack_name@ --resource @init_resource@ --region @aws_region@ --configsets setup
/usr/local/bin/cfn-init --stack @stack_name@ --resource @init_resource@ --region @aws_region@ --configsets run

/usr/local/bin/cfn-signal -e 0 --stack @stack_name@ --resource @signal_resource@ --region @aws_region@