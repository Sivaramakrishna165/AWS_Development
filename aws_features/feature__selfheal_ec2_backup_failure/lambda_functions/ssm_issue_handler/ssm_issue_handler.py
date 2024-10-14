"""
This Lambda function is used to check the status  if SSM Agent is present on an instance or not.

This Lambda is a part of Selfheal ec2 backup failure.

In dxcms_sh_bf_sfn_diagnosis state machine(CheckSSM)
gets executed after Wait start of startInstance.
In dxcms_sh_bf_sfn_resolution State machine(CheckSSM)
gets executed after Wait start of startInstance.

Input event of the lambda function is:
    {
        "instance_id" : "<instance-id>", 
        "Instance_State" : "running/stopped"
    }

In Diagnosis state machine,
On successful check, next state - CheckCli is called.
On FAILURE, next State CheckSSMError and then NotifyForLambaFunctionFailure.
In Resolution state machine, 
On successful check, next state - CheckCLIRemediation is called.
On FAILURE, next State CheckSSMError and then NotifyForLambaFunctionFailure.

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
        input = {"error" : str(e), "resource_id" : instance_id, "resource_type" : "EC2 Instance"}
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


#Input to this function from event: "instance_id" and 'Instance_State'
#This function calls get_status funtion
#It return event with "Instance_SSM_Status", "SSM_Agent_Version", "SSM_Ping_Status" and "Instance_State" keys
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
        Instance_State = event['Instance_State']

        Instance_SSM_Status, SSM_Agent_Version, Ping_Status, error_status = get_status(instance_id)
        if not error_status:
            event["Instance_SSM_Status"] = Instance_SSM_Status
            event["SSM_Agent_Version"] = SSM_Agent_Version
            event["SSM_Ping_Status"] = Ping_Status
            event["Instance_State"] = Instance_State
            print(event)
            return success_token(event,task_token)
        else:
            raise Exception("Error while checking ssm status and ping status.")
    except Exception as e:
        print("Error lambda_handler() - ",e)
        if not error_status:
            error_status = traceback.format_exc()
        input = {"error" : f"Error lambda_handler() - {str(e)}", "resource_id" : instance_id, "resource_type" : "EC2 Instance"}
        return failure_token(task_token, input, error_status)

#Input: instance_id
#It calls describe_instance_information method from ssm boto3 client.
#This function returns Instance_SSM_Status, SSM_Agent_Version and Ping_Status.
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

#Checks if 'InstanceInformationList' list is empty or not.
#If list is empty, it returns Instance_SSM_Status as 'Not_Present', with some other values.
#If list is not empty, it returns Instance_SSM_Status as 'Present' with current version and ping status
        if not response['InstanceInformationList']:
            Instance_SSM_Status = 'Not_Present'
            SSM_Agent_Version = 'Not_Present'
            Ping_Status = 'Connection_Lost'
        else:
            Instance_SSM_Status = 'Present'
            SSM_Agent_Version = response['InstanceInformationList'][0]['AgentVersion']
            Ping_Status = response['InstanceInformationList'][0]['PingStatus']
        
        return Instance_SSM_Status, SSM_Agent_Version, Ping_Status, error_status
    except Exception as e:
        print("Error get_status() - ",e)
        error_status = traceback.format_exc()
        return "", "", "", error_status
    


event1 = {"instance_id" : "i-0f4adf69c733b6c84"}

if __name__ == "__main__":
    lambda_handler(event1,"")