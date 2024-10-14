"""
    This Lambda function is used to check 
    platform_type(Windows/Linux),platform_name,architecture,ssm_ping_status(online or offline).

    This Lambda is a part of Selfheal Cloudwatch agent failure.
    In dxcms_sh_cs_sfn_diagnosis state machine(FetchInstanceDetails)
    and gets executed after CheckIAMRole.
    In dxcms_sh_cs_sfn_resolution state machine(FetchInstanceDetails)
    and gets executed after RemediateIAMRoleIssue.

    Input event of the lambda function is:
        {
	        "instance_id":"<instance-id>"
        }
    In Diagnosis state machine,
    On successful check, next state -CheckCWAgentDetails is called
    On FAILURE, next State FetchInstanceDetailsError and then NotifyForLambaFunctionFailure.
    In resolution state machine,
    On successful check, next state - RestartCWAgent is called.
    On FAILURE, next State FetchInstanceDetailsError and then NotifyForLambaFunctionFailure.

"""

import json
import boto3
import sys
from botocore.config import Config


config=Config(retries=dict(max_attempts=10,mode='standard'))


# '''
#     This function will return the Line 
#     number and the error that occured.
# '''
# def PrintException():
#     exc_type, exc_obj, tb = sys.exc_info()
#     f = tb.tb_frame
#     lineno = tb.tb_lineno
#     captureErr = "Line No. : " + str(lineno)  + " | ERROR: " + str(exc_obj)
#     return captureErr


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
            error = str(error),
            cause = cause
        )
        print('failure task token sent - ',sf_response)
    except Exception as e:
        print("Error failure_token() - ", e)
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
            return False, False
        else:
            response = response[0]
        print("Response: ", response)

    except Exception as e:
        error_flag = True
        # print(PrintException())
        print("Error get_config_details() - ",e)
        print("Error Ocurred during describe_instance_information")

    else:
        return response, error_flag
    
    return False, error_flag


# def token(event, task_token):

#     sf = boto3.client('stepfunctions')
#     sf_output = json.dumps(event)
#     # task_token = event['token']

#     sf_response = sf.send_task_success(
#         taskToken=task_token,
#         output=str(sf_output)
#     )

#     return sf_response


def lambda_handler(event,context):
    
    error_status = False
    print("Event Recieved: ", event)
    task_token = event['token']
    event = event["Payload"]
    input = {"resource_id" : event["instance_id"], "resource_type" : "EC2 Instance"}
        
    try:
        ec2 = boto3.resource('ec2', config=config)
        instance_id = event["instance_id"]
        
        response, error_status = get_config_details(instance_id)
        
        if response:
            if response['PingStatus'] == 'Online':
                event['platform_type'] = response['PlatformType']
                event['platform_name'] = response['PlatformName'] 
                event['architecture'] = ec2.Instance(instance_id).architecture 
                event['ssm_ping_status'] = 'Online'
                # event['Instance_SSM_Status'] = 'Present'

                # return event
                print("Returning Event: ",event)
                return success_token(event,task_token)
        
        print("SSM_Ping_Status is not Online")   
        event['ssm_ping_status'] = 'Offline' 
        print("Returning Event: ",event)
        # return token(event, task_token)

    except Exception as e:
        # print(PrintException())
        print("Error lambda_handler() - ",e)
        error_status = True
        input["error"] = "Something Went Wrong"
        return failure_token(task_token, input, e)
    
    return success_token(event,task_token)
         
    
event1 = {"instance_id":"i-0d5758a7ec1373272"}
#   'i-011b47c2f1a5352cf'

if __name__ == "__main__":
    lambda_handler(event1,"")

