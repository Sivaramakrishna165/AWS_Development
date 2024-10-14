"""
   This Lambda function is used to check 
    platform_type(Windows/Linux),platform_name,architecture,os_flavour,public_ip_address(present or not_present),
    ssm_ping_status(online or offline).

    This Lambda is a part of Selfheal crowdstrike agent failure.
    In dxcms_sh_cs_sfn_diagnosis state machine(FetchInstanceDetails)
    and gets executed after CheckIAMRole.
    In dxcms_sh_cs_sfn_resolution state machine(FetchInstanceDetails)
    and gets executed after RemediateIAMRoleIssue.
   
    Input event of the lambda function is:
        {
	    "instance_id":"<instance-id>"
        }
    
    In Diagnosis state machine,
    On successful check, next state - CheckCLIStatus is called.
    On FAILURE, next State FetchInstanceDetailsError and then NotifyForLambaFunctionFailure.
    In resolution state machine,
    On successful check, next state - RemediateCLIIssue is called.
    On FAILURE, next State FetchInstanceDetailsError and then NotifyForLambaFunctionFailure.
"""

import json
import boto3
import sys
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

'''
    This function returns the response from
    the ssm describe_instance_information and
    the error status.
'''
def get_config_details(instance_id):
    error_flag = False
    print("get_config_details called")

    ssm = boto3.client('ssm', config=config)

    try:
        print("Getting Instance Information.")
        response = ssm.describe_instance_information(Filters=[{ 'Key': 'InstanceIds', 'Values': [instance_id]}])['InstanceInformationList']
        if not response:
            return {}, True
        else:
            response = response[0]
        print("Response: ", response)

    except Exception as e:
        error_flag = traceback.format_exc()
        # print(PrintException())
        print("Error get_config_details() - ",e)
        print("Error Ocurred during describe_instance_information")

    else:
        return response, error_flag
    
    return {}, error_flag


def get_os_flovour(PlatformName):
    print("get_os_flovour called")

    os_flavour = ['windows', 'oracle', 'ubuntu', 'sles', 'debian', 'centos', 'red hat', 'amazon']

    for os in os_flavour:
        if str(PlatformName).lower().find(os) != -1:
            print(PlatformName.lower())
            return os
    
    return "Not Found"

def lambda_handler(event,context):
    global task_token, instance_id
    error_status = False
    print("Event Recieved: ", event)
    task_token = event['token']
    event = event["Payload"]
    instance_id = event["instance_id"]
    input = {"resource_id" : instance_id, "resource_type" : "EC2 Instance"}
        
    try:
        ec2 = boto3.resource('ec2', config=config)
        instance_id = event["instance_id"]
        response, error_status = get_config_details(instance_id)
        if response:
            if response['PingStatus'] == 'Online':
                event['platform_type'] = response['PlatformType']
                event['platform_name'] = response['PlatformName'] 
                event['architecture'] = ec2.Instance(instance_id).architecture
                event['public_ip_address'] = "not_present" if ec2.Instance(instance_id).public_ip_address == None else "present"
                event['os_flavour'] = get_os_flovour(response['PlatformName'])  
                event['ssm_ping_status'] = 'Online'
                return success_token(event,task_token)   

        print("SSM_Ping_Status is not Online")  
        event['ssm_ping_status'] = 'offline'
    except Exception as e:
        print("Error lambda_handler() - ",e)
        # print(PrintException())
        if not error_status:
            error_status = traceback.format_exc()

        input["error"] = "Something Went Wrong"
        return failure_token(task_token, input, error_status)
        
    else:
        print(event)
        # if not error_status:
        return success_token(event,task_token)
        
    
event1 = {"instance_id":"i-0d5758a7ec1373272"}
#   'i-011b47c2f1a5352cf'

if __name__ == "__main__":
    lambda_handler(event1,"")

