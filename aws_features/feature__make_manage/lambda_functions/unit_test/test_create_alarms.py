'''
This is the Unit Test file for create_alarm.py
'''

import boto3, pytest
import sys,csv
sys.path.append('../make_manage')
from moto import mock_ssm, mock_ec2, mock_s3, mock_cloudformation
from create_alarms import create_alarms
EXAMPLE_AMI_ID = "ami-12c6146b"

temp_stack_name = 'test-mock'
@mock_ec2
def test_get_volume_type():
    ec2_resource = boto3.resource('ec2', 'us-east-1')
    create_alarms_obj = create_alarms('us-east-1')
    result = ec2_resource.create_instances(
        ImageId=EXAMPLE_AMI_ID,
        MinCount=1,
        MaxCount=1,
        BlockDeviceMappings=[
            {
                "DeviceName": "/dev/sda1",
                "Ebs": {"VolumeSize": 50, "DeleteOnTermination": True},
            }
        ],
    )
    instance = result[0]
    instance_volume_ids = []
    for volume in instance.volumes.all():
        instance_volume_ids.append(volume.volume_id)
    volume_type = create_alarms_obj.get_volume_type(instance_volume_ids[0])

@mock_ec2
@mock_ssm
def test_ssm_send_cmd():
    ec2_resource = boto3.resource('ec2', 'us-east-1')
    create_alarms_obj = create_alarms('us-east-1')
    result = ec2_resource.create_instances(
        ImageId=EXAMPLE_AMI_ID,
        MinCount=1,
        MaxCount=1,
        BlockDeviceMappings=[
            {
                "DeviceName": "/dev/sda1",
                "Ebs": {"VolumeSize": 50, "DeleteOnTermination": True},
            }
        ],
    )
    instance = result[0]
    instance_volume_ids = []

    for volume in instance.volumes.all():
        instance_volume_ids.append(volume.volume_id)
    
    create_alarms_obj.ssm_send_cmd(instance.id,"/dev/sda1", 'source' )

@mock_ec2
def test_get_instance_volumes():
    ec2_resource = boto3.resource('ec2', 'us-east-1')
    create_alarms_obj = create_alarms('us-east-1')
    result = ec2_resource.create_instances(
        ImageId=EXAMPLE_AMI_ID,
        MinCount=1,
        MaxCount=1,
        BlockDeviceMappings=[
            {
                "DeviceName": "/dev/sda1",
                "Ebs": {"VolumeSize": 50, "DeleteOnTermination": True},
            }
        ],
    )
    instance = result[0]
    
    create_alarms_obj.get_instance_volumes(instance.id)

@mock_ec2
def test_get_instance_type():
    ec2_resource = boto3.resource('ec2', 'us-east-1')
    create_alarms_obj = create_alarms('us-east-1')
    result = ec2_resource.create_instances(
        ImageId=EXAMPLE_AMI_ID,
        MinCount=1,
        MaxCount=1,
        BlockDeviceMappings=[
            {
                "DeviceName": "/dev/sda1",
                "Ebs": {"VolumeSize": 50, "DeleteOnTermination": True},
            }
        ],
    )
    instance = result[0]
    
    create_alarms_obj.get_instance_type(instance.id)

@mock_s3
def test_read_s3_object():
    key_name = 'testkey'
    bucket = 'bucket'
    create_alarms_obj = create_alarms('us-east-1')
    s3 = boto3.client("s3", region_name='us-east-1')
    s3.create_bucket(Bucket=bucket)
    s3.put_object(Bucket=bucket, Key=key_name, Body="key_value")
    create_alarms_obj.read_s3_object(bucket,key_name )
    # body = conn.Object("mybucket", "test-bucket").get()["Body"].read().decode()

@mock_s3
def test_s3_upload_object():
    key_name = 'testkey.json'
    file_name = 'testfile.csv'
    report = [{'Test':'Mock'}]
    bucket = 'bucket'
    create_alarms_obj = create_alarms('us-east-1')
    s3 = boto3.client("s3", region_name='us-east-1')
    s3.create_bucket(Bucket=bucket)
    # s3.put_object(Bucket=bucket, Key=key_name, Body="key_value")
    keys = report[0].keys()
    with open(file_name, 'w', newline='') as output_file:
        dict_writer = csv.DictWriter(output_file, keys)
        dict_writer.writeheader()
        dict_writer.writerows(report)
    create_alarms_obj.s3_upload_object(file_name, bucket,'testkey')

  
if __name__ == "__main__":
    # test_get_volume_type()    
    test_s3_upload_object()