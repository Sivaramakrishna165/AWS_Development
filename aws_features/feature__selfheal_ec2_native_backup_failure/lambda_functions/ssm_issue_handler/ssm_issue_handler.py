"""
This Lambda function is used to check the status if SSM Agent is present on an instance or not.
This also check the current Ping Status

This Lambda is a part of Selfheal EC2 NativeBackupFailure

In Diagnosis state machine (dxcms_sh_nbf_sfn_diagnosis):
gets executed after - CheckIAMRole State
On successful check, next state - CheckCLI is called.
On FAILURE, next State - TriggerNotificationSfnWError and NotifyForLambaFunctionFailure.

In Resolution state machine (dxcms_sh_nbf_sfn_resolution):
gets executed after - Wait and IAMRoleRemediation
On successful check, next state - CLIRemediation is called.
On FAILURE, next State - TriggerNotificationSfnWError and NotifyForLambaFunctionFailure.

"""

import json
import boto3
import os
import traceback
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))

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
        failure_token(task_token, str(e)[:200], traceback.format_exc())

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
    global task_token,instance_id
        
    print("input recieved to this script - " + str(event))
    task_token = event["token"]
    event = event["Payload"]
    instance_id = event["instance_id"]
    error_status = False
    try:
        ssm_client = boto3.client('ssm',config=config)
        ec2_client = boto3.client('ec2',config=config)

        Instance_SSM_Status, Ping_Status, error_status = get_status(instance_id)
        if not error_status:
            event["Instance_SSM_Status"] = Instance_SSM_Status
            event["SSM_Ping_Status"] = Ping_Status
            event["wait_time"] = event["wait_time"] - 60
            print(event)
            return success_token(event,task_token)
        else:
            raise Exception("Error while checking ssm status and ping status.")
    except Exception as e:
        print("Error lambda_handler() - ",e)
        if not error_status:
            error_status = traceback.format_exc()
        return failure_token(task_token, str(e)[:200], error_status)

def get_status(instance_id):
    error_status = False
    try:
        print("get_status() triggered.")
        ssm_client = boto3.client('ssm',config=config)
        response = ssm_client.describe_instance_information(
            InstanceInformationFilterList=[
                { 'key': 'InstanceIds', 'valueSet': [ instance_id, ] },
            ],
        )
        if not response['InstanceInformationList']:
            Instance_SSM_Status = 'Not_Present'
            Ping_Status = 'Connection_Lost'
        else:
            Instance_SSM_Status = 'Present'
            Ping_Status = response['InstanceInformationList'][0]['PingStatus']
        
        return Instance_SSM_Status, Ping_Status, error_status
    except Exception as e:
        print("Error get_status() - ",e)
        error_status = traceback.format_exc()
        return "", "", error_status