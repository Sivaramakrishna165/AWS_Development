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
    global task_token, resource_id
    print("input recieved to this script - " + str(event))
    error = False
    task_token = event["token"]
    event = event["Payload"]
    try:
        event_name = event["sh_result"]["Event"]
        try:
            if "resource_id" in event["sh_result"]:
                resource_id = event["sh_result"]["resource_id"]
            else:
                resource_id = event["sh_result"]["instance_id"]
        except:
            resource_id = "Not_Known"
        try:    
            AccountId = boto3.client('sts',config=config).get_caller_identity().get('Account')
        except:
            error = traceback.format_exc()
            raise Exception(f"Error while reading AccountId. Incident in Service Now is NOT created for {resource_id}.")
        
        arn_prefix = "arn:aws:states:" + region + ":" + AccountId + ":stateMachine:"

        resource_type = "EC2_Instance"
        if (event_name == "CrowdStrikeFalconAgentFailure"):    
            short_message = f"AWS_SH_CS {AccountId} {region} | CrowdStrike/Falcon Agent is NOT installed for {resource_id}."
        elif (event_name == "CloudWatchAgentLogFailure"):
            short_message = f"AWS_SH_CW {AccountId} {region} | CloudWatch Logs for {resource_id} are missing."
        elif (event_name == "BackupFailure"):
            short_message = f"AWS_SH_BF {AccountId} {region} | level 2 backup for {resource_id} does not exist in last 1440 mins"
        elif (event_name == "Ec2NativeBackupFailure"):
            short_message = f"AWS_SH_NBF {AccountId} {region} | Native Backup for {resource_id} does not exist in last 1440 mins"
        elif (event_name == "LambdaAnomalyDetection"):
            short_message = f"AWS_SH_LAD {AccountId} {region} | Lambda Functions Anomaly Detected."
            resource_type = "LambdaAnomalyCloudWatchAlarm"
        else:
            short_message = f"AWS_SH {AccountId} {region} | SelfHeal step function caught an error."

        event["errorInfo"] = event["sh_result"].pop("errorInfo")
        long_message = f"SelfHeal Master Step Function caught error. Details : {str(event['sh_result'])}."

        notification_event = {
            "resource_id":resource_id,
            "long_message":long_message,
            "short_message":short_message,
            "account_id":AccountId,
            "Resolution_Validation":False,
            "resource_type":resource_type
        }

        error = trigger_stepfunction(notification_event, arn_prefix + "dxcms_sh_sfn_notification")
        if error:
            raise Exception(f"Error while triggering dxcms_sh_sfn_notification step function. Incident in Service Now is NOT created for {resource_id}.")

        return success_token(event,task_token)
    except Exception as e:
        print("Error lambda_handler() - ",e)
        if not error:
            error = traceback.format_exc()
        return failure_token(task_token, str(e)[:200], error)
