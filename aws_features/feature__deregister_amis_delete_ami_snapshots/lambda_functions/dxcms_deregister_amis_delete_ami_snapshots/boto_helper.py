import boto3
from botocore.config import Config
from datetime import date
from datetime import *
  
class boto_helper():
    def __init__(self, region):
        config=Config(retries=dict(max_attempts=10,mode='standard'))
        sts_client = boto3.client('sts', config = config)
        self.ec2_client = boto3.client('ec2', config = config, region_name = region)
        self.ssm_client = boto3.client('ssm', config = config, region_name = region)
        self.account = sts_client.get_caller_identity()['Account']
        today = date.today()
        y, m, d = [int(x) for x in str(today).split('-')]
        self.today = date(y, m, d)
    
    def get_ssm_param_val(self, name):
        try:
            response = self.ssm_client.get_parameter(Name=name)
            return response['Parameter']['Value']
        except Exception as e:
            print('Error get_ssm_param_val()-',e)
            raise e
        
    def describe_amis(self):
        try:
            image_list = []
            response = self.ec2_client.describe_images(
                Filters=[
                    {
                        'Name': 'tag:DeleteOn',
                        'Values': [
                            '*',
                        ]
                    },
                ],
                Owners=[
                    'self',
                ],
            )
            
            # Filter the AMIs where DeleteOn value lesser than current date
            for image in response['Images']:
                for tag in image['Tags']:
                    if(tag['Key'] == 'DeleteOn' and tag['Value'] != ''):
                        try:
                            deleteon_tag_val = tag['Value']
                            y, m, d = [int(x) for x in deleteon_tag_val.split('-')]
                            deleteon = date(y, m, d)
                            if(deleteon <= self.today):
                                image_list.append({'ImageId':image['ImageId'], 'DeleteOn': tag['Value']})
                                break
                        except Exception as e:
                            print('Failed to get DeleteOn for AMI - {} - Error - {}'.format(image['ImageId'], e))
            
            return image_list
        except Exception as e:
            print('Error describe_ami()',e)
    
    def describe_ami_snapshots(self, ami_snapshot_desc):
        try:
            snapshots_list = []
            extra_args = {}
            extra_args['Filters'] = [
                    {
                        'Name': 'status',
                        'Values': [
                            'completed'
                        ]
                    },
                    {
                        'Name': 'tag:DeleteOn',
                        'Values': [ '*' ]
                    },
                    {
                        'Name': 'owner-id',
                        'Values': [
                            self.account,
                        ]
                    },
                    {
                        'Name': 'description',
                        'Values': ami_snapshot_desc
                    },
                ]
            extra_args['OwnerIds']=[self.account]

            while True:
                response = self.ec2_client.describe_snapshots(**extra_args)
                for snap in response['Snapshots']:
                    for tag in snap['Tags']:
                        if(tag['Key'] == 'DeleteOn' and tag['Value'] != ''):
                            try:
                                deleteon_tag_val = tag['Value']
                                y, m, d = [int(x) for x in deleteon_tag_val.split('-')]
                                deleteon = date(y, m, d)
                                if(deleteon <= self.today):
                                    snapshots_list.append({'SnapshotId':snap['SnapshotId'], 'DeleteOn': tag['Value']})
                                    break
                            except Exception as e:
                                print('Failed to get DeleteOn for AMI snap - {} - Error - {}'.format(snap['SnapshotId'], e))
                if('NextToken' in response):
                    extra_args['NextToken'] = response['NextToken']
                else:
                    break

            return snapshots_list

        except Exception as e:
            print('Error describe_ami_snapshots()',e)
            
    
    def de_register_ami(self, image):
        try:
            self.ec2_client.deregister_image(
                ImageId=image['ImageId']
            )
            print('Deregister Initiated - {} DeleteOn - {}'.format(image['ImageId'], image['DeleteOn']))
        except Exception as e:
            print('Error - de_register_ami()',e)
    
    def delete_snapshot(self, snap):
        try:
            self.ec2_client.delete_snapshot(
                    SnapshotId=snap['SnapshotId']
            )
            print('Delete snapshot Initiated - {} DeleteOn - {}'.format(snap['SnapshotId'], snap['DeleteOn']))
        except Exception as e:
            print('Error - delete_snapshot()',e)
  