"""
This lambda script is used to trigger the next step function. 
It uses the name of the state machine to check which step function to trigger and passes the appropriate 
event into the next state machine.

This Lambda is a part of Selfheal EC2 NativeBackupFailure

In Diagnosis state machine (dxcms_sh_nbf_sfn_diagnosis):
gets executed after - DynamoDbLogging State
On successful check, next state - End
On FAILURE, next State - TriggerNotificationSfnWError and NotifyForLambaFunctionFailure.

In Resolution state machine (dxcms_sh_nbf_sfn_resolution):
gets executed after - DynamoDbLogging
On successful check, next state - End
On FAILURE, next State - TriggerNotificationSfnWError and NotifyForLambaFunctionFailure.

In ExecuteBackup state machine (dxcms_sh_nbf_sfn_execute_backup):
gets executed after - SnowDescriptionInput
On successful check, next state - End
On FAILURE, next State - TriggerNotificationSfnWError and NotifyForLambaFunctionFailure.
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
    instance_id = event["instance_id"]
    error_status = False
    try:
        AccountId = boto3.client('sts',config=config).get_caller_identity().get('Account')
        arn_prefix = "arn:aws:states:" + region + ":" + AccountId + ":stateMachine:"

        if (event["statemachine_name"].find('diagnosis') != -1):
            resolution_event = {
                "Flag":"Fix", "selfHealJobId":event["selfHealJobId"],
                "instance_id":event["instance_id"], "backup_level_assigned": event["backup_level_assigned"],
                "instance_os_type":event["instance_os_type"], "retention_period":event["retention_period"],
                "vault_name":event["vault_name"], "backup_role_name":event["backup_role_name"],
                "instance_state":event["instance_state"], "unmounted_volumes":event["unmounted_volumes"],
                "unmounted_volume_ids":event["unmounted_volume_ids"], "Event":event["Event"]
                }
            error_status = trigger_stepfunction(resolution_event, arn_prefix + "dxcms_sh_nbf_sfn_resolution")
            if error_status:
                raise Exception(f"Error trigger_stepfunction(): Error while triggering dxcms_sh_bf_sfn_resolution step function.")
        elif (event["statemachine_name"].find('resolution') != -1):
            execute_backup_event = {
                "selfHealJobId":event["selfHealJobId"], "instance_id":event["instance_id"],
                "backup_level_assigned":event["backup_level_assigned"], "instance_os_type":event["instance_os_type"],
                "retention_period":event["retention_period"], "vault_name":event["vault_name"],
                "backup_role_name":event["backup_role_name"], "instance_state":event["instance_state"],
                "issue_resolution_status":event["issue_resolution_status"], "Instance_SSM_Status":event["Instance_SSM_Status"],
                "region":region, "account_id": AccountId, "instance_iam_status":event["instance_iam_status"],
                "backup_iam_status":event["backup_iam_status"], "Instance_CLI_Status":event["Instance_CLI_Status"],
                "Instance_Tags_Status":event["Instance_Tags_Status"], "Event":event["Event"]
                }
            error_status = trigger_stepfunction(execute_backup_event, arn_prefix + "dxcms_sh_nbf_sfn_execute_backup")
            if error_status:
                raise Exception(f"Error trigger_stepfunction(): Error while triggering dxcms_sh_bf_sfn_execute_backup step function.")
        elif (event["statemachine_name"].find('execute_backup') != -1):
            error_status = trigger_stepfunction(event["notification_sfn_payload"], arn_prefix + "dxcms_sh_sfn_notification")
            if error_status:
                raise Exception(f"Error trigger_stepfunction(): Error while triggering dxcms_sh_sfn_notification step function.")

        return success_token(event,task_token)
    except Exception as e:
        print("Error lambda_handler() - ",e)
        if not error_status:
            error_status = traceback.format_exc()
        return failure_token(task_token, str(e)[:200], error_status)