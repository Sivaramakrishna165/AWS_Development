"""
This Lambda function is used to start ec2 instance whose instance id given as input

In dxcms_sh_bf_sfn_diagnosis state machine(StartInstance)
gets executed after ChoiceStartToStartInstance.
In dxcms_sh_bf_sfn_resolution state machine(StartInstance)
gets executed after ChoiceStartToStartInstance.


Input event of the lambda function is:
    {
        "instance_id" : "<instance-id>", 
    }

In Diagnosis state machine,
On successful check, next state - waitstate to check SSM is called.
On FAILURE, next State StartInstanceError and then NotifyForLambaFunctionFailure.
In Resolution state machine, 
On successful check, next state - waitstate to check SSM is called.
On FAILURE, next State StartInstanceError and then NotifyForLambaFunctionFailure.

"""

import json
import boto3
import os,sys
import time
import traceback
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))

def success_token(event, task_token):
    try:
        print("success_token() triggered.")
        sf = boto3.client('stepfunctions', config=config)
        sf_output = json.dumps(event)
        sf_response = sf.send_task_success(
            taskToken=task_token,
            output=str(sf_output)
        )
        print("success task token sent - ", sf_response)
        return sf_response
    except Exception as e:
        print("Error success_token() - ", e)
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
        sf = boto3.client('stepfunctions', config=config)
        sf_response = sf.send_task_failure(
            taskToken=taskToken,
            error=json.dumps(error),
            cause=cause
        )
        print('failure task token sent - ', sf_response)
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
        instance_id = event['instance_id']
        Instance_State = event['Instance_State']
        InstanceStateChangedTo = ''
        if Instance_State == 'stopped':
            response,error_status = run_instance(instance_id)
            if not error_status:
                InstanceStateChangedTo = 'running'  
            else:
                raise Exception("Error run_instance() - Error while starting the instance")    
        event['InstanceStateChangedTo'] = InstanceStateChangedTo
        return success_token(event,task_token)
    except Exception as e:
        print("Error lambda_handler() - ", e)
        if not error_status:
            error_status = traceback.format_exc()
        input = {"error" : f"Error lambda_handler() - {str(e)}", "resource_id" : instance_id, "resource_type" : "EC2 Instance"}
        return failure_token(task_token, input, error_status)

def run_instance(instance_id):
    error_status = False
    try:
        print("run_instance() triggered")
        ec2 = boto3.resource('ec2', config=config)
        instance = ec2.Instance(instance_id)
        response = instance.start()
        print('Running the Instance')
        instance.wait_until_running()
        print('Instance is running but waiting for it to be ready')
        # time.sleep(120)
        print('Ready to do operation')
        return response, error_status
    except Exception as e:
        error_status = traceback.format_exc()
        print("Error run_instance() - ", e)
        return '', error_status