"""
Generates long description and short description from the diagnosis result.
Returns the payload required for creating ServiceNow incident/event, which is to be
passed to notification step function.

This Lambda is a part of Selfheal EC2 NativeBackupFailure

In ExecuteBackup state machine (dxcms_sh_nbf_sfn_execute_backup):
gets executed after - SendEmail
On successful check, next state - TriggerNotificationSFN
On FAILURE, next State - TriggerNotificationSfnWError and NotifyForLambaFunctionFailure.
"""

import json
import boto3
import os
from botocore.config import Config
import traceback

config=Config(retries=dict(max_attempts=10,mode='standard'))

db_client = boto3.client('dynamodb',config=config)
ec2_resource = boto3.resource('ec2',config=config)
region = os.environ['AWS_REGION']
table_name = os.environ['table_name']

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

def compile_data(compile_event):
    error_status = False
    try:
        print("compile_data() triggered.")
        long_message = {}
        lm_keys = ["backup_validation","selfHealJobId","instance_id","instance_os_type","vault_name",
                      "instance_state","Instance_SSM_Status","instance_iam_status","backup_iam_status","Instance_CLI_Status",
                      "Instance_Tags_Status","region","account_id","execution_id","statemachine_name"]
        for key in lm_keys:
            if key in compile_event.keys():
                long_message[key] = compile_event[key]
        long_message['DynamoDB_Table'] = table_name
        if "backup_validation" in compile_event.keys():
            if not compile_event["backup_validation"]:
                if "backup_job_output" in compile_event.keys():
                    long_message["recovery_point_arn"] = compile_event["backup_job_output"]["recovery_point_arn"]
                    long_message["backup_job_id"] = compile_event["backup_job_output"]["backup_job_id"]
                    long_message["backup_state"] = compile_event["backup_job_output"]["state"]
                if "recovery_point_output" in compile_event.keys():
                    long_message["recovery_point_status"] = compile_event["recovery_point_output"]["recovery_point_status"]

        try:
            AccountName = boto3.client('iam',config=config).list_account_aliases()['AccountAliases'][0]
            account_id = boto3.client('sts',config=config).get_caller_identity().get('Account')
        except:
            AccountName = compile_event["account_id"]
            account_id = compile_event["account_id"]

        short_message = f"AWS {AccountName} {region} | Native Backup for {compile_event['instance_id']} created"
        if "backup_validation" in compile_event:
            if compile_event["backup_validation"] == False:
                short_message = f"AWS_SH_NBF {AccountName} {region} | Native Backup for {compile_event['instance_id']} does not exist in last 1440 mins"

        print(f"long message: {long_message}")
        print(f"short message: {short_message}")

        return long_message, short_message, error_status
    except Exception as e:
        print("Error compile_data() - ",e)
        if not error_status:
            error_status = traceback.format_exc()
        return "", "", "", error_status

def lambda_handler(event, context):
    global task_token, instance_id
        
    print("input recieved to this script - " + str(event))
    task_token = event["token"]
    event = event["Payload"]
    instance_id = event["instance_id"]
    error_status = False
    try:
        long_message, short_message, error_status = compile_data(event)
        if "backup_validation" in event:
            Resolution_Validation = event["backup_validation"]
        else:
            Resolution_Validation = False
        if not error_status:
            new_event = {"notification_sfn_payload":{
                "account_id":event["account_id"], "instance_id":event["instance_id"], "resource_type":"EC2Instance",
                "Resolution_Validation":Resolution_Validation, "selfHealJobId":event["selfHealJobId"],"long_message":long_message,
                "short_message":short_message, "Event":event["Event"], "region": event["region"]},
                "statemachine_name":event["statemachine_name"], "instance_id":event["instance_id"]
                }
        else:
            raise Exception(f"Error compile_data(). Unable to compile data for SNow Incident.")        
        return success_token(new_event,task_token)
    except Exception as e:
        print("Error lambda_handler() - ",e)
        if not error_status:
            error_status = traceback.format_exc()
        return failure_token(task_token, str(e)[:200], error_status)