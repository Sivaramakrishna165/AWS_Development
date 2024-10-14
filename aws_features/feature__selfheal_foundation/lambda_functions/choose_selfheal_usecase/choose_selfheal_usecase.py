"""
This Lambda function is a part of feature__selfheal_foundation stepfuction.
Note: Input(payload) for this script is passed through SNS topic.
Based on this input(payload) value, this lambda calls appropriate step-function.
Payload:cs
{
	"InstanceId":"<instance-id>","OldStateValue":"OK","NewStateValue":"ALARM",
	"EventDate":"2022-05-30T07:21:40.269Z","Event":"CrowdStrikeFalconAgentFailure",
	"IncidentPriority":"3","region":"eu-west-2"
}
payload:cw
{
	"instanceId":"<instance-id>","logGroupName":"/var/log/messages or Default-Log-Group",
	"logStreamName":"<instance-id>","OldStateValue":"OK","NewStateValue":"ALARM",
	"EventDate":"2022-05-30T07:21:40.269Z","Event":"CloudWatchAgentLogFailure",
	"IncidentPriority":"3","region":"eu-west-2"
}
Payload:bf
{
	"InstanceId":"<instance-id>","VolumeIds":[<vol-id>"],"LatestBackup":"2022-08-21T12:13:29.864Z","EventDate":"2022-08-22T07:13:40.269Z",
	"Event":"BackupFailure","IncidentPriority":"3","region":"ap-southeast-1"
}
In dxcms_sh_sfn_self_heal_master_sfn,
On successful check, next state machine diagnosis step function is called.
On FAILURE, next State choose_selfheal_usecase_error and then Notify_failure.
"""

import json
import boto3
import os
import traceback
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))

stepfunction_client = boto3.client('stepfunctions',config=config)

ec2_backup_failure_sfn_arn = os.environ['ec2_backup_failure_sfn_arn']
cw_agent_failure_sfn_arn = os.environ['cw_agent_failure_sfn_arn']
cs_agent_failure_sfn_arn = os.environ['cs_agent_failure_sfn_arn']
ec2_cloudwatch_alarms_sfn_arn = os.environ['ec2_cloudwatch_alarms_sfn_arn']
ec2_native_backup_failure_sfn_arn = os.environ['ec2_native_backup_failure_sfn_arn']
lam_anomaly_detection_sfn_arn = os.environ['lam_anomaly_detection_sfn_arn']

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
    global task_token, resource_id, event_name, resource_type
    print("input recieved to this script - " + str(event))
    task_token = event["token"]
    event = event["Payload"]
    resource_id = event["resource_id"]
    resource_type = event["resource_type"]
    event_name = event["Event"]
    try:

        if (event["Event"] == "BackupFailure"):
            event["instance_id"] = event.pop("resource_id")
            error = stepfunction_call(event, ec2_backup_failure_sfn_arn)
            if error:
                raise Exception(f"Error while calling step function : {ec2_backup_failure_sfn_arn}")
        elif (event["Event"] == "CloudWatchAgentLogFailure"):
            event["instance_id"] = event.pop("resource_id")
            error = stepfunction_call(event, cw_agent_failure_sfn_arn)
            if error:
                raise Exception(f"Error while calling step function : {cw_agent_failure_sfn_arn}")
        elif (event["Event"] == "CrowdStrikeFalconAgentFailure"):
            event["instance_id"] = event.pop("resource_id")
            error = stepfunction_call(event, cs_agent_failure_sfn_arn)
            if error:
                raise Exception(f"Error while calling step function : {cs_agent_failure_sfn_arn}")
        elif (event["Event"] == "EC2CloudWatchAlarms"):
            error = stepfunction_call(event, ec2_cloudwatch_alarms_sfn_arn)
            if error:
                raise Exception(f"Error while calling step function : {ec2_cloudwatch_alarms_sfn_arn}")
        elif (event["Event"] == "Ec2NativeBackupFailure"):
            event["instance_id"] = event.pop("resource_id")
            error = stepfunction_call(event, ec2_native_backup_failure_sfn_arn)
            if error:
                raise Exception(f"Error while calling step function : {ec2_native_backup_failure_sfn_arn}")
        elif (event["Event"] == "LambdaAnomalyDetection"):
            error = stepfunction_call(event, lam_anomaly_detection_sfn_arn)
            if error:
                raise Exception(f"Error while calling step function : {lam_anomaly_detection_sfn_arn}")
        else:
            error = "Wrong payload passed. Check Event key in payload. Only accepted values are BackupFailure | CloudWatchAgentLogFailure | CrowdStrikeFalconAgentFailure | EC2CloudWatchAlarms | LambdaAnomalyDetection."
            raise Exception("Wrong Event passed in payload. No step function called.")

        return success_token(event,task_token)

    except Exception as e:
        print("Error lambda_handler() - ",e)
        if not error:
            error = traceback.format_exc()
        return failure_token(task_token, str(e)[:200], error)


def stepfunction_call(event_data, step_func_arn):
    error = False
    try:
        print("stepfunction_call() triggered.")
        response = stepfunction_client.start_execution(
            stateMachineArn = step_func_arn,
            input = json.dumps(event_data)
        )
        print("Step_Function Called.")
    except Exception as e:
        print("Error stepfunction_call() - ",e)
        error = traceback.format_exc()
        print(error)
    finally:
        return error