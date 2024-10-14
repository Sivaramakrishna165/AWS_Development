'''
Boto Helper class contain all the supported aws api operations
'''

import boto3
from botocore.config import Config

class primary_boto_helper():
    
    def __init__(self):
        self.config = Config(retries=dict(max_attempts=10,mode='standard'))
        self.state_client = boto3.client('stepfunctions', config = self.config)
        self.ec2_client = boto3.client('ec2', config = self.config)
        self.ec2_resource = boto3.resource('ec2', config = self.config)
        self.ssm_client = boto3.client('ssm', config = self.config)
        
    #To get the status of the instance
    def instance_status_check(self, instance_id):
        
        try:
            status_types = ["shutting-down","terminated","stopping","stopped"]
            instance = self.ec2_resource.Instance(instance_id)
            instancestatus = instance.state['Name']
            
            if instancestatus not in status_types:
                instance.wait_until_running()
                
                print("The status of the instance {} is - {}".format(instance_id, instancestatus))
                
                instancestatuswaiter = self.ec2_client.get_waiter('instance_status_ok')
                instancestatuswaiter.wait(InstanceIds=[instance_id])
                print("Instance status check is completed")
    
                systemstatuswaiter = self.ec2_client.get_waiter('system_status_ok')
                systemstatuswaiter.wait(InstanceIds=[instance_id])
                print("system status check is completed")                
        
        except Exception as e:
            print('ERROR -', e)
            raise
        
    #To get the instance osname
    def get_instance_osname(self, instance_id):
        
        try:
            response = self.ssm_client.describe_instance_information(
            Filters=[
                
                {
                        'Key': 'InstanceIds',
                        'Values': [instance_id]
                }
            ]
            )
            
            osname = response['InstanceInformationList'][0]['PlatformName']
            return osname
        
        except Exception as e:
            print('Error -', str(e))
            raise
        
    #To get the instance os achitecture
    def get_instance_os_arch(self, instance_id):
        
        try:
            response = self.ec2_client.describe_instances(
                InstanceIds=[instance_id]
            )
            
            osarch = response['Reservations'][0]['Instances'][0]['Architecture']
            return osarch
            
        except Exception as e:
            print('ERROR -', str(e))
            raise
            
    #To update the tag value on the instance        
    def update_tag(self, InstId, key, value):
        
        try:
            update_tag_response = self.ec2_client.create_tags(
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
            print("update_tag_response is ", update_tag_response)
            
        except Exception as e:
            print("ERROR in update_tag", e)
            
    #To invoke the step function    
    def call_state_machine(self,state_machine_input, state_fun_arn):
        
        try:
            state_start_response = self.state_client.start_execution(
            stateMachineArn=state_fun_arn,
            input=state_machine_input
            )
            
            print("state_start_response is ", state_start_response)
            
        except Exception as e:
            print(str(e) + " exception in call_state_machine")