'''
Boto Helper class contain all the supported aws api operations
'''

import boto3
import time

class primary_boto_helper():
    
    #To verify the whether the edr tag value is Activated
    def verify_instance_tag(self, ec2_client, instance_id):
        
        try:
            response = ec2_client.describe_instances(
                InstanceIds=[instance_id]
                )
            instance_tags = response['Reservations'][0]['Instances'][0]['Tags']
            for tag in instance_tags:
                if tag['Key'] == 'edr':
                    if tag['Value'] == 'Activated':
                        return True
            return False
            
        except Exception as e:
            print('ERROR -',str(e))
            
    #To update the tag value on the instance        
    def update_tag(self, ec2_client, InstId, key, value):
        
        try:
            update_tag_response = ec2_client.create_tags(
                Resources=[
                    InstId,
                ],
                Tags=[
                    {
                        'Key': key,
                        'Value': value
                    },
                ]
            )
            print('The instance {} tag has been updated'.format(InstId))
        except Exception as e:
            print("Error in update_tag", e)