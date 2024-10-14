'''
This Lambda function checks status of the rebooted instances and updates the reboot sequence
'''

import boto3
import json
import sys
import os
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))

ssm_client_document = boto3.client('ssm',config=config)

def PrintException():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    captureErr = "Line No. : " + str(lineno)  + " | ERROR: " + str(exc_obj)
    return captureErr
 
def check_instance_type(instance_id):
    ec2_client = boto3.client("ec2",region_name = region,config=config)
    response = ec2_client.describe_instances(InstanceIds=[instance_id,])
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            try:
                platform = instance['Platform']
            except:
                platform = 'linux'
    return platform

def check_instance_status(instance_id):
    client = boto3.client('ec2',region_name = region,config=config)
    try:
        response = client.describe_instance_status(InstanceIds=[instance_id,])
        Instance_status = response['InstanceStatuses'][0]['InstanceState']['Name']
        #print("Instance status:",Instance_status)
        if Instance_status:
            return Instance_status
    except:
        error = PrintException()
        print(error)
        if error:
            Instance_status = 'Not Running'
        return Instance_status

# fetch the document hash value
def get_document_hash(document_name):
    try:
        response = ssm_client_document.describe_document(
            Name=document_name
        )
        hash_value = response['Document']['Hash']
    except Exception as e:
        hash_value = ''
    return hash_value

def check_window_server_reachability(instance_id):
    try:
        document_hash = get_document_hash('AWS-RunPowerShellScript')
        response = ssm_client.send_command(
            InstanceIds=[
                instance_id,
            ],
            DocumentName='AWS-RunPowerShellScript',
            DocumentHash = document_hash,
            DocumentHashType='Sha256',
            TimeoutSeconds=300,
            Parameters={
                'commands': ["hostname",]
            },
            OutputS3BucketName=S3_Bucket_Name,
            OutputS3KeyPrefix=S3_prefix  )
        command_id = response['Command']['CommandId']
        print("Command_Id : ",command_id)
        if command_id :
            server_reachability = 'Yes'
        return server_reachability
    except:
        error = PrintException()
        print("Error : ",error)
        if error:
            server_reachability = 'No'
        return server_reachability


def check_linux_server_reachability(instance_id):
    try:
        document_hash = get_document_hash('AWS-RunShellScript')
        response = ssm_client.send_command(
            InstanceIds=[
                instance_id,
            ],
            DocumentName='AWS-RunShellScript',
            DocumentHash=document_hash,
            DocumentHashType='Sha256',
            TimeoutSeconds=300,
            Parameters={
                'commands': ["hostname",]
            },
            OutputS3BucketName=S3_Bucket_Name,
            OutputS3KeyPrefix=S3_prefix )
        command_id = response['Command']['CommandId']
        print("Command_Id : ",command_id)
        if command_id :
            server_reachability = 'Yes'
        return server_reachability
    except:
        error = PrintException()
        print("Error : ",error)
        if error:
            server_reachability = 'No'
        return server_reachability

   
def lambda_handler(event, context):
    try:
        global S3_Bucket_Name, S3_directory_name, S3_folder, region, ssm_client, S3_prefix
        
        tagValue = event['PatchInstallOn']
        S3_Bucket_Name = event['S3_Bucket']
        S3_directory_name = event['S3_directory_name']
        S3_folder = event['S3_Folder_Name']
        S3_prefix = S3_folder +"/PATCHING/"+S3_directory_name+"/reboot_logs"
        #print("Reboot Logs path:",S3_Bucket_Name, S3_prefix)
        
        region = event['region']
        ssm_client = boto3.client('ssm',region_name = region,config=config)

        reboot_sequence = event['Updated_reboot_sequence']
        print("Reboot Sequence Received:",reboot_sequence)
        
        if 'Updated_reboot_status_check' in event.keys():
            reboot_status_check = event['Updated_reboot_status_check']
        else:
            reboot_status_check = {}
        
        if 'status_check_retries' in event.keys():
            status_check_retries =  event['status_check_retries']
        else:
            status_check_retries = {}
        
        updated_reboot_sequence = {}
        updated_reboot_status_check = {}
                
        #checking status of previously rebooted instances
        for sequence in [reboot_sequence, reboot_status_check]:
            for key, dependents in sequence.items():
                rebooted_instance_status = check_instance_status(key)
                instance_platform = check_instance_type(key)
                if instance_platform == 'linux': #If Platform is Linux
                    server_reachable_after_reboot = check_linux_server_reachability(key)
                else : #If Platform is Windows
                    server_reachable_after_reboot = check_window_server_reachability(key)
                print("Key Server:",key)
                print("Status after reboot:- Instance Status:", rebooted_instance_status, "Server Reachable:",server_reachable_after_reboot)
                if rebooted_instance_status == 'running' and server_reachable_after_reboot == 'Yes':
                    if len(dependents)>1:
                        updated_reboot_sequence[dependents[0]] = dependents[1:]
                    elif len(dependents)==1:
                        updated_reboot_sequence[dependents[0]]=[]
                else:
                    print("Key Server",key,"not reachable.")
                    updated_reboot_status_check[key] = dependents[:]
                    if key in status_check_retries.keys():
                        status_check_retries[key] = status_check_retries[key]+1
                    else:
                        status_check_retries[key] = 1
        
        event['Updated_reboot_sequence'] = updated_reboot_sequence    
        event['Updated_reboot_status_check'] = updated_reboot_status_check   
        event['status_check_retries'] = status_check_retries
        print(event)
        if not (len(updated_reboot_sequence) or len(updated_reboot_status_check)):
            print("No Dependents pending reboot and all servers are up and running")
            event.pop('Updated_reboot_sequence')
            event.pop('Updated_reboot_status_check')
            event.pop('status_check_retries')


        return event
    except:
        print(PrintException())
       
# sample test case
if __name__ == "__main__":
    
    event1 = {
	"PatchInstallOn": "testing-JUN_7_2023_13_5_4HRS_BY_AY",
	"S3_Bucket": "dxcms.patchingautomation.567529657087.us-west-1",
	"S3_directory_name": "MAY_2023/us-west-1/patchJobId_7ec67b43-feae-11ed-b007-57d89e3b79a7",
	"CommandId": "49ec2b9c-822c-409b-8ed7-0c4ccfc7ecee",
	"Status": "pending",
	"app_action": "start",
	"S3_Folder_Name": "patching_reports",
	"region": "us-west-1",
	"Updated_reboot_sequence": {
		"i-000e0d7a28e744d41": [
			"i-0e457c2b98360a88a",
			"i-08706c4829273c6f5"
		]
	},
	"Wait_time": 120,
	"Updated_reboot_status_check": {},
	"status_check_retries": {}
    }
    lambda_handler(event1, "")     
