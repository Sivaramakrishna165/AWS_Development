"""
    This Lambda function is used to returns the status of that command
    along with the reason of failure, in case it fails or cancels.

    This Lambda is a part of Selfheal ec2 backup failure.
    In dxcms_sh_bf_sfn_execute_backup state machine(CheckSSMCommandStatus)
    gets executed after WaitForSSMCommand.

    Input event of the lambda function is:
    {
        "command_id":"xxxx-xxxx-xxxx-xxxx", 
        "instance_id":"<instance_id>"
    }

    In dxcms_sh_bf_sfn_execute_backup 
    On successful check, next state checkcmdstatus called
    On FAILURE, next State CheckSSMCommandStatusError and then NotifyForLambaFunctionFailure.

"""

import json
import traceback
import boto3
import os
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))

ec2_client = boto3.client('ec2', config=config)
ssm_client = boto3.client('ssm', config=config)
ec2_resource = boto3.resource('ec2', config=config)
log_client = boto3.client('logs', config=config)

log_group_name = os.environ['log_group_name']

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

def check_command_status(command_id):
    cmd_error = False
    try:
        print("check_command_status() triggered.")
        response = ssm_client.list_command_invocations(
            CommandId=command_id
        )

        print("Command Status: " + response['CommandInvocations'][0]['Status'])

        return response['CommandInvocations'][0]['Status'], cmd_error
    
    except Exception as e:
        print("Error check_command_status() - ",e)
        cmd_error = True
        return '', cmd_error

def cancel_command(command_id):
    try:
        print("cancel_command() triggered.")
        response = ssm_client.cancel_command(
            CommandId=command_id
        )
        print("Command cancelled.")
    
    except Exception as e:
        print("Error cancel_command() - ",e) 

def fail_reason(event):
    try:
        print("fail_reason() triggered.")
        failure_reason = ""

        if(event['Instance_Platform'] == "Windows"):
            log_stream_name = event['command_id'] + "/" + event['instance_id'] + "/" + 'runPowerShellScript/stdout'
            response = log_client.get_log_events(
                logGroupName=log_group_name,
                logStreamName= log_stream_name,
                startFromHead=True
            )
            for msg in response['events']:
                failure_reason = failure_reason + msg['message'].replace('\n',' ')

        elif(event['Instance_Platform'] == "Linux"):
            log_stream_name = event['command_id'] + "/" + event['instance_id'] + "/" + 'LinuxLevel2Backup/stdout'
            response = log_client.get_log_events(
                logGroupName=log_group_name,
                logStreamName= log_stream_name,
                startFromHead=True
            )
            for msg in response['events']:
                failure_reason = failure_reason + msg['message'].replace('\n',' ')

        return failure_reason
    
    except Exception as e:
        print("Error fail_reason() - ",e)
        return 'Not_Known'

def lambda_handler(event, context):
    global task_token, instance_id
        
    print("input recieved to this script - " + str(event))
    task_token = event["token"]
    event = event["Payload"]
    instance_id=event["instance_id"]
    try:
        command_id = event['command_id']
        failure_reason = "Not Known"

        command_status, cmd_error = check_command_status(command_id)
        if not cmd_error:
            if (command_status == 'Success'):
                status = 'success'
                failure_reason = None
            elif (command_status == 'Pending' or command_status == 'InProgress'):
                print("Command not completed, cancelling.")
                cancel_command(command_id)
                status = 'failed'
                failure_reason = "Taking more time than expected. Run Command Cancelled/Terminated."
            elif (command_status == 'Cancelled'):
                status = 'failed'
                failure_reason = "command got automatically cancelled"
            else:
                print("Command Failed.")
                status = 'failed'
                failure_reason = fail_reason(event)
        else:
            status = 'failed'
            failure_reason = f"Error while checking run command status for command id {command_id}"

        print("reason for failure - " + str(failure_reason))
        event['run_command_status'] = status

        return success_token(event,task_token)   
    except Exception as e:
        print("Error lambda_handler() - ",e)
        error_status = traceback.format_exc()
        input = {"error" : f"Error lambda_handler() - {str(e)}", "resource_id" : instance_id, "resource_type" : "EC2 Instance"}
        return failure_token(task_token, input, error_status)