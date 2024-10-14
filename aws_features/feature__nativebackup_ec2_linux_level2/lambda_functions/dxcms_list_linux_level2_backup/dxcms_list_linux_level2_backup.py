# This lambda function will list all the linux instances having tag-value: LinuxNativeBackupLevel-2(This code will skip the windows instance having this tag-value) 
# and if its in running state it trigger the step function. If its in stopped state it will create a on demand backup job
#This lambda doesnt require event input

import json
import boto3
import os
from time import sleep

def main():
    try:
        instance_details=[]
        region=os.environ["AWS_REGION"]
        step_fn_arn=os.environ["STEP_FUNCTION_ARN"]
        iam_role_arn=os.environ["IAM_ROLE_ARN"]
        backup_vault_name=os.environ["BACKUP_VAULT_NAME"]
        tag_name=os.environ["TAG_KEY"]
        tag_value=os.environ["TAG_VALUE"]
        retention_period=os.environ["RETENTION_PERIOD"]

        ec2_client = boto3.client('ec2',region_name=region)
        sts_client = boto3.client('sts',region_name=region)
        sf_client = boto3.client('stepfunctions',region_name=region)
        backup_client=boto3.client('backup')
        account_no=sts_client.get_caller_identity()['Account']
        
        paginator = ec2_client.get_paginator('describe_instances')
        response_iterator = paginator.paginate(Filters=[{'Name': 'tag:{}'.format(tag_name),'Values': [tag_value]}])
        for iterator in response_iterator:
            if iterator['Reservations']:
                instance_details.extend({"instance_id":instance['InstanceId'],"state":instance['State']['Name']} for instance_reservation in iterator['Reservations'] for instance in instance_reservation['Instances'] if 'Platform' not in instance)
            else:
                print("Instances are not available having tag {} and value {}".format(tag_name,tag_value))
            #if 'Platform' not in instance:
            #instance_info={}
            #instance_details.append(instance['InstanceId'])
            #instance_info["os_name"]= [tags['Value'] for tags in instance['Tags'] if tags['Key']=='OSName'][0]
            #instance_details.append(instance_info)
        for instance in instance_details:
            if instance["state"]=="running":
                print("Instance: {} sending payload to step function".format(instance["instance_id"]))
                step_fn_input={"Instance_id": [instance["instance_id"]],"Account_id":account_no,"region":region,"retention_period":{"DeleteAfterDays": int(retention_period)}}
                input_sfn=json.dumps(step_fn_input)
                try:
                    sleep(0.8)
                    sf_client.start_execution(stateMachineArn=step_fn_arn,input=input_sfn)
                    print('Step function {} triggered successfully for instance {}'.format(step_fn_arn,instance["instance_id"]))
                except Exception as e:
                    print('Step function {} failed to trigger for instance {}'.format(step_fn_arn,instance["instance_id"]))
                    print(str(e))
            else:
                print("Instance {} is in stopped state, taking level 1 backup.".format(instance["instance_id"]))
                try:
                    backup_client.start_backup_job(BackupVaultName=backup_vault_name,ResourceArn="arn:aws:ec2:{}:{}:instance/{}".format(region,account_no,instance["instance_id"]),IamRoleArn=iam_role_arn,Lifecycle={'DeleteAfterDays': int(retention_period)})
                    print("Successfully triggered backup job for the instance {}".format(instance["instance_id"]))
                except Exception as e:
                    print("Backup Job failed to trigger for the instance {}".format(instance["instance_id"]))

    except Exception as e:
        print("Error-",e)
             

def lambda_handler(event, context):
    print("Received Event: ",event)
    main()
    

