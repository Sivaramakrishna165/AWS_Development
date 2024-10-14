"""
This lambda reads the output of the execution of dxcms_Linux_Level2_Backup state machine
Fetches the status of backup job
If backup job status is completed, returns the arn of recovery point

This Lambda is a part of Selfheal EC2 NativeBackupFailure

In ExecuteBackup state machine (dxcms_sh_nbf_sfn_execute_backup):
gets executed after - LinuxLevel2Backup
On successful check, next state - CheckSfnStatus
On FAILURE, next State - BackupFailure
"""

import json
import boto3
import traceback
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))

sfn_client = boto3.client('stepfunctions', config=config)
backup_client = boto3.client('backup', config=config)

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

def read_recovery_point(backup_job_result):
    error_status = False
    try:
        print("read_recovery_point() triggered.")
        job_response = backup_client.describe_backup_job(
            BackupJobId=backup_job_result['Backup_job_id']
        )
        backup_job_output = {
            "backup_job_id": job_response['BackupJobId'], "state": job_response['State'],
            "backup_vault_name": job_response['BackupVaultName'], "recovery_point_arn": job_response['RecoveryPointArn']
        }
        return backup_job_output, error_status
    except Exception as e:
        print("Error read_recovery_point() - ", e)
        return {}, traceback.format_exc()

def lambda_handler(event, context):
    global task_token,instance_id

    print("input recieved to this script - " + str(event))
    task_token = event["token"]
    event = event["Payload"]
    instance_id = event['instance_id']
    error_status = False
    try:
        execution_arn = event.pop("sfn_call_response")["execution_arn"]
        sfn_execution_response = sfn_client.describe_execution(
            executionArn = execution_arn
        )
        if sfn_execution_response['status'] == 'SUCCEEDED':
            linux_lvl2_sfn_output = json.loads(sfn_execution_response['output'])
            if linux_lvl2_sfn_output['Result_describe_backup_job']['State'] == 'COMPLETED':
                backup_job_output, error_status = read_recovery_point(linux_lvl2_sfn_output['Result_describe_backup_job'])
                event["backup_sfn_validation"] = True
                if error_status:
                    return Exception("Error read_recovery_point() - error while reading recovery point arn")
            else:
                print(f"linux level 2 backup job '{linux_lvl2_sfn_output['Result_describe_backup_job']['Backup_job_id']}' is not completed successfully.")
                event["backup_sfn_validation"] = False
                backup_job_output = {}
        else:
            print(f"step function execution with arn '{execution_arn}' is exited with status {sfn_execution_response['status']}")
            event["backup_sfn_validation"] = False
            backup_job_output = {}
        event["backup_job_output"] = backup_job_output
        return success_token(event,task_token)
    except Exception as e:
        print("Error lambda_handler() - ",e)
        if not error_status:
            error_status = traceback.format_exc()
        return failure_token(task_token, str(e)[:200], error_status)