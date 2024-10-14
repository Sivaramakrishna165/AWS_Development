"""
This lambda script is used to trigger the next step function. 
It uses the name of the state machine to check which step function to trigger and passes the appropriate 
event into the next state machine.

In Diagnosis state machine,
On successful check,Resolution state machine is triggered.
On failure, next state TriggerDiagnosisSfn Error and then NotifyForLambaFunctionFailure.
In resolution state machine,
On successful check,Execute Backup state machine is triggered.
On failure, next state TriggerResolutionSfn Error and then NotifyForLambaFunctionFailure.
In Execute Backup state machine,
On successful check,notification state machine is triggered.
On failure, next state TriggerNotificationSfn Error and then NotifyForLambaFunctionFailure.
"""

import json
import boto3
import os
import traceback
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))

stepfunction_client = boto3.client('stepfunctions',config=config)

region = os.environ['AWS_REGION']

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

def trigger_stepfunction(event_data, step_func_arn):
    error_status = False
    try:
        print("trigger_stepfunction() triggered.")
        response = stepfunction_client.start_execution(
            stateMachineArn = step_func_arn,
            input = json.dumps(event_data)
        )

        print("stepFunction Triggered.")
        return error_status
    except Exception as e:
        print("Error trigger_stepfunction() - ",e)
        error_status = traceback.format_exc()
        return error_status

def lambda_handler(event, context):
    global task_token,instance_id
        
    print("input recieved to this script - " + str(event))
    task_token = event["token"]
    event = event["Payload"]
    if ("instance_id" in event):
        instance_id = event["instance_id"]
    else:
        instance_id = event[0]["instance_id"]
    try:
        AccountId = boto3.client('sts',config=config).get_caller_identity().get('Account')
        arn_prefix = "arn:aws:states:" + region + ":" + AccountId + ":stateMachine:"

        if (event[1]["StateMachine"].find('diagnosis') != -1):
            resolution_event = {"Flag":"Fix","selfHealJobId":event[0]["selfHealJobId"],"instance_id":event[0]["instance_id"],"unmounted_volumes":event[0]["unmounted_volumes"],"unmounted_volume_ids":event[0]["unmounted_volume_ids"]}
            error_status = trigger_stepfunction(resolution_event, arn_prefix + "dxcms_sh_bf_sfn_resolution")
            if error_status:
                raise Exception(f"Error trigger_stepfunction(): Error while triggering dxcms_sh_bf_sfn_resolution step function.")
        elif (event[1]["StateMachine"].find('resolution') != -1):
            execute_backup_event = {"selfHealJobId":event[0]["selfHealJobId"],"instance_id":event[0]["instance_id"],"Issue_Resolution_Status":event[0]["Issue_Resolution_Status"],"Instance_SSM_Status":event[0]["Instance_SSM_Status"]}
            error_status = trigger_stepfunction(execute_backup_event, arn_prefix + "dxcms_sh_bf_sfn_execute_backup")
            if error_status:
                raise Exception(f"Error trigger_stepfunction(): Error while triggering dxcms_sh_bf_sfn_execute_backup step function.")
        elif (event[1]["StateMachine"].find('execute_backup') != -1):
            notification_event = {
                "selfHealJobId":event[0]["selfHealJobId"],
                "instance_id":event[0]["instance_id"],
                "long_message":event[0]["long_message"],
                "short_message":event[0]["short_message"],
                "Backup_Validation_Status":event[0]["Backup_Validation_Status"],
                "EbsVolumeBackupLevel":event[0]["EbsVolumeBackupLevel"],
                "Resolution_Validation":event[0]["Resolution_Validation"],
                "account_id":event[0]["account_id"],
                "resource_type":event[0]["resource_type"]
                }
            error_status = trigger_stepfunction(notification_event, arn_prefix + "dxcms_sh_sfn_notification")
            if error_status:
                raise Exception(f"Error trigger_stepfunction(): Error while triggering dxcms_sh_sfn_notification step function.")

        return success_token(event,task_token)
    except Exception as e:
        print("Error lambda_handler() - ",e)
        if not error_status:
            error_status = traceback.format_exc()
        input = {"error" : f"Error lambda_handler() - {str(e)}", "resource_id" : instance_id, "resource_type" : "EC2 Instance"}
        return failure_token(task_token, input, error_status)