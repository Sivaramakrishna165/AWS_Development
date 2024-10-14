"""
This Lambda function is used to check the status of IAM role(default role or other role) attached to an instance or not
This lambda also check the status of backup IAM role, whether req policies are attached or not
If the Flag:Fix key is passed: This lambda fixes the issues, by attaching the role to the ec2 instance
and by also attaching the required policies to IAM role.

This Lambda is a part of Selfheal EC2 NativeBackupFailure

In Diagnosis state machine (dxcms_sh_nbf_sfn_diagnosis):
gets executed after - CheckTags State
On successful check, next state - CheckSSM is called.
On FAILURE, next State - TriggerNotificationSfnWError and NotifyForLambaFunctionFailure.

In Resolution state machine (dxcms_sh_nbf_sfn_resolution):
gets executed after - TagsRemediation
On successful check, next state - Wait and then CheckSSM is called.
On FAILURE, next State - TriggerNotificationSfnWError and NotifyForLambaFunctionFailure.
"""

import json
import boto3
import os
import traceback
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))

ec2_client = boto3.client('ec2',config=config)
iam_client = boto3.client('iam',config=config)
ssm_client = boto3.client('ssm',config=config)

default_arn = os.environ['DefaultIAMRoleArn']
req_backup_policies = os.environ['req_backup_policies']

def success_token(event,task_token):
    try:
        print("success_token() triggered.")
        sf = boto3.client('stepfunctions',config=config)
        sf_output = json.dumps(event)
        sf_response = sf.send_task_success(
            taskToken=task_token,
            output=str(sf_output)
        )
        print("success task token sent - ", sf_response)
        return sf_response
    except Exception as e:
        print("Error success_token() - ",e)
        print("not able to send task success token.")
        input = str(e)[:200]
        failure_token(task_token, input, traceback.format_exc())

def failure_token(taskToken, error, err_cause):
    try:
        print("failure_token() triggered.")
        if isinstance(err_cause, dict):
            cause = json.dumps(err_cause)
        else:
            cause = str(err_cause)
        sf = boto3.client('stepfunctions',config=config)
        sf_response = sf.send_task_failure(
            taskToken=taskToken,
            error = json.dumps(error),
            cause = cause
        )
        print('failure task token sent - ',sf_response)
    except Exception as e:
        print("Error failure_token() - ", e)
        print("not able to send failure task token")
        raise

def lambda_handler(event, context):
    global task_token, instance_id
        
    print("input recieved to this script - " + str(event))
    task_token = event["token"]
    event = event["Payload"]
    instance_id = event["instance_id"]
    backup_role_name = event["backup_role_name"]
    error_status = False
    try:
        instance_profile_arn = get_instance_profile_arn(instance_id)
        ec2_policies = False
        if instance_profile_arn:
            if instance_profile_arn == default_arn:
                instance_iam_role = "default_role"
                ec2_policies = True
            else:
                instance_iam_role = "other_role"
        else:
            instance_iam_role = "no_role"
        attached_backup_policies, error_status = list_backup_policies(backup_role_name)
        if not error_status:
            if set(req_backup_policies.split(',')).issubset(set(attached_backup_policies)):
                backup_policies = True
            else:
                backup_policies = False
        else:
            raise Exception(f"Error while fetching policies from iam role {backup_role_name}")
        if check_key(event):
            if instance_iam_role == "no_role":
                status = attach_role(instance_id)
                if status:
                    instance_iam_role = "default_role"
                    ec2_policies = True
            elif instance_iam_role == "other_role":
                status = attach_snapshot_policy(instance_profile_arn)
                if status:
                    ec2_policies = True
            else:
                ec2_policies = True
            
            if not backup_policies:
                status = attach_backup_policies(req_backup_policies.split(','), backup_role_name)
                if status:
                    backup_policies = True
        if ec2_policies:
            instance_iam_status = "present"
        else:
            instance_iam_status = "not_present"
        if backup_policies:
            backup_iam_status = "present"
        else:
            backup_iam_status = "not_present"
        event["instance_iam_status"] = instance_iam_status
        event["instance_iam_role"] = instance_iam_role
        event["backup_iam_status"] = backup_iam_status
        event["wait_time"] = 300
        return success_token(event,task_token)
    except Exception as e:
        print("Error lambda_handler() - ",e)
        if not error_status:
            error_status = traceback.format_exc()
        return failure_token(task_token, str(e)[:200], error_status)

def get_instance_profile_arn(instance_id):
    instance_profile_arn = None
    try:
        print("get_instance_profile_arn() triggered.")
        response = ec2_client.describe_iam_instance_profile_associations(
            Filters=[{'Name': 'instance-id', 'Values': [instance_id,]},],
        )
        if response['IamInstanceProfileAssociations']:
            instance_profile_arn = (response['IamInstanceProfileAssociations'][0]['IamInstanceProfile']['Arn'])
        print("instance_profile_arn is " + str(instance_profile_arn))
        return instance_profile_arn
    except Exception as e:
        print("Error get_instance_profile_arn() - ",e)
        print(f"Unable to read iam role arn of instance {instance_id}")
        return failure_token(task_token, str(e)[:200], traceback.format_exc())
        
def list_backup_policies(backup_role_name):
    print("list_backup_policies() triggered.")
    error_status = False
    try:
        response = iam_client.list_attached_role_policies(RoleName=backup_role_name)
        attached_backup_policies = []
        for policy in response['AttachedPolicies']:
            attached_backup_policies.append(policy['PolicyName'])
        return attached_backup_policies, error_status
    except Exception as e:
        print(f"Error list_backup_policies() - {e}")
        return [], traceback.format_exc()
    
def attach_role(instance_id):
    try:
        print("attach_role() triggered.")
        name = default_arn.split('/')[-1]
        ec2_client.associate_iam_instance_profile(
            IamInstanceProfile={'Name': name},
            InstanceId= instance_id
        )
        print(f"{name} iam instance profile attached to the instance {instance_id}")
        return True
    except Exception as e:
        print("Error attach_role() - ",e)
        print(f"Unable to attach role {name} to instance {instance_id}.")
        return False
    
def attach_backup_policies(req_backup_policies, backup_role_name):
    try:
        print("attach_backup_policies() triggered.")
        for policy in req_backup_policies:
            iam_client.attach_role_policy(
                RoleName=backup_role_name,
                PolicyArn=f"arn:aws:iam::aws:policy/service-role/{policy}"
            )
        return True
    except Exception as e:
        print("Error attach_backup_policies() - ",e)
        return False
    
def attach_snapshot_policy(instance_profile_arn):
    try:
        print("attach_snapshot_policy() triggered.")
        role_name=(instance_profile_arn.split('/'))[-1]
        response1 = iam_client.get_instance_profile(
            InstanceProfileName=role_name)
        role_instance=response1['InstanceProfile']['Roles'][0]['RoleName']

        default_role_name=(default_arn.split('/'))[-1]
        response2 = iam_client.get_instance_profile(
            InstanceProfileName=default_role_name)
        default_role_instance=response2['InstanceProfile']['Roles'][0]['RoleName']

        policy_document = iam_client.get_role_policy(
            RoleName=default_role_instance,
            PolicyName='SnapshotPolicy'
        )

        response3 = iam_client.put_role_policy(
            RoleName=role_instance,
            PolicyName='SnapshotPolicy',
            PolicyDocument=json.dumps(policy_document['PolicyDocument'])
        )
        print(f"'SnapshotPolicy inline policy attached to instance role {role_name}")
        return True
    except Exception as e:
        print("Error attach_backup_policies() - ",e)
        return False
    
def check_key(event):
    try:
        print("check_key triggered.")
        if 'Flag' in event.keys():
            if event['Flag'] == 'Fix':
                return True 
        return False
    except Exception as e:
        print("Error check_key() - ",e)
        return failure_token(task_token, str(e)[:200], traceback.format_exc())