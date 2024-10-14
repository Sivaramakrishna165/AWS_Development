"""
This Lambda function is a part of feature__selfheal_foundation stepfuction.
This lambda script is used to trigger the next step function. 
It uses the name of the state machine to check which step function to 
trigger and passes the appropriate event into the next state machine.

In dxcms_sh_sfn_self_heal_master_sfn,
On successful check, next state machine dxcms_sh_sfn_notifications is called.
On FAILURE, next State trigger_notification_snf_error and then Notify_Failure.
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
    error = False
    try:
        print("trigger_stepfunction() triggered.")
        response = stepfunction_client.start_execution(
            stateMachineArn = step_func_arn,
            input = json.dumps(event_data)
        )

        print("stepFunction Triggered.")
    except Exception as e:
        print("Error trigger_stepfunction() - ",e)
        error = traceback.format_exc()
    finally:
        return error

def lambda_handler(event, context):
    global task_token, resource_id, event_name, resource_type
    print("input recieved to this script - " + str(event))
    error = False
    task_token = event["token"]
    event = event["Payload"]
    resource_id = event["resource_id"]
    resource_type = event["resource_type"]
    event_name = event['Event']
    try:
        AccountId = boto3.client('sts',config=config).get_caller_identity().get('Account')
        try:
            AccountName = boto3.client('iam',config=config).list_account_aliases()['AccountAliases'][0]
        except:
            AccountName = ""
        
        arn_prefix = "arn:aws:states:" + region + ":" + AccountId + ":stateMachine:"

        if (event["Event"] == "BackupFailure"):
            short_message = "AWS_SH_BF " + AccountId + " " + region + " | " + "level 2 backup for " + event['resource_id'] + " does not exist in last 1440 mins"
        elif (event["Event"] == "CloudWatchAgentLogFailure"):
            short_message = "AWS_SH_CW " + AccountId + " " + region + " | " + "CloudWatch Logs for " + event['resource_id'] + " are missing."
        elif (event["Event"] == "CrowdStrikeFalconAgentFailure"):
            short_message = "AWS_SH_CS " + AccountId + " " + region + " | " + "CrowdStrike/Falcon Agent is NOT installed for " + event['resource_id'] + "."
        elif (event["Event"] == "Ec2NativeBackupFailure"):
            short_message = f"AWS_SH_NBF {AccountId} {region} | Native Backup for {event['resource_id']} does not exist in last 1440 mins"
        elif (event["Event"] == "LambdaAnomalyDetection"):
            short_message = f"AWS_SH_LAD {AccountId} {AccountName} {region} | Lambda Functions Anomaly Detected."

        long_message = str(event)

        notification_event = {
            "selfHealJobId":event["selfHealJobId"],
            "instance_id":event["resource_id"],
            "long_message":long_message,
            "short_message":short_message,
            "account_id":AccountId,
            "Resolution_Validation":False,
            "resource_type":resource_type
        }

        error = trigger_stepfunction(notification_event, arn_prefix + "dxcms_sh_sfn_notification")
        if error:
            raise Exception("Error while triggering dxcms_sh_sfn_notification step function. Not triggered. Incident not created.")

        event["short_message"] = short_message
        event["account_id"] = AccountId
        print(f"event returned: {str(event)}")
        return success_token(event,task_token)
    
    except Exception as e:
        print("Error lambda_handler() - ",e)
        if not error:
            error = traceback.format_exc()
        return failure_token(task_token, str(e)[:200], error)