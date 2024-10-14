import pytest
import sys
sys.path.append('../dxcms_deregister_amis_delete_ami_snapshots')
from boto_helper import boto_helper
from moto import mock_ec2, mock_sts
from moto.ec2.models import OWNER_ID
from moto.ec2.models.amis import AMIS
from moto.core import ACCOUNT_ID
import json
from boto3 import Session
import boto3
import argparse

EXAMPLE_AMI_ID = "ami-12c6146b"
EXAMPLE_AMI_ID2 = "ami-03cf127a"
EXAMPLE_AMI_PARAVIRTUAL = "ami-fa7cdd89"
EXAMPLE_AMI_WINDOWS = "ami-f4cf1d8d"



@mock_ec2
@mock_sts
def test_describe_amis():
    ec2 = boto3.client("ec2", region_name="us-east-1")

    reservation = ec2.run_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
    instance = reservation["Instances"][0]
    instance_id = instance["InstanceId"]

    image_id = ec2.create_image(
        InstanceId=instance_id, Name="test-ami", Description="Created by CreateImage",
        TagSpecifications=[
        {
            'ResourceType': 'image',
            'Tags': [
                {
                    'Key': 'DeleteOn',
                    'Value': '2022-01-01'
                },
            ]
        },
    ]
    )["ImageId"]

    boto_helper_obj = boto_helper('us-east-1')
    amis = boto_helper_obj.describe_amis()
    snaps = boto_helper_obj.describe_ami_snapshots()
    assert amis, image_id

        

   
