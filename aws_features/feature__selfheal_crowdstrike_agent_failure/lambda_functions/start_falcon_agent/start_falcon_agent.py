'''
    This Lambda function is used to restart the Falcon Agent 
    and return the status of restart wheather its success or failed.

    This Lambda is a part of Selfheal crowdstrike agent failure.
    In dxcms_sh_cs_sfn_resolution state machine(RestartFalconAgent)
    gets executed after RemediateCLIIssue.

    Input event of the lambda function is:
    {
	"instance_id":"<instance-id>",
	"ssm_ping_status":"Online",
	"platform_type":"Linux/Windows",
	"falcon_agent_status":"installed_not_running/installed"
    }

    In resolution state machine,
    On successful check, next state ChoiceRestartValidation
    On FAILURE, next State RestartFalconAgentError and then NotifyForLambaFunctionFailure.
'''

import json
import boto3
import sys
import time
import traceback
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))

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

'''
    This function returns the command required to 
    check the start time of Falcon agent and the 
    document required tio run the command.
'''
def cs_status_data(event):
    print("cw_restart_data called")

    if event["platform_type"] == "Windows":
        script = "AWS-RunPowerShellScript"
        command = ["Get-Date (Get-Process CsFalconService).StartTime",
                    "(Get-Service -Name CsFalconService).status"
        ]
    else:
        script = "AWS-RunShellScript"
        command = ["sudo systemctl status falcon-sensor | grep Active"]

    return script, command


'''
    This function returns the restart commands 
    for the Falcon agent and the document required 
    to run the command.
'''
def cs_restart_data(event):
    print("cw_restart_data called")

    if event["platform_type"] == "Windows":
        script = "AWS-RunPowerShellScript"
        command = [
                    "Restart-Service CsFalconService",
                    "Get-Date (Get-Process CsFalconService).StartTime"
                ]
    else:
        script = "AWS-RunShellScript"
        command = [
                    "sudo systemctl restart falcon-sensor",
                    "sudo systemctl status falcon-sensor | grep Active"
                ]

    return script, command


'''
    The function runs the command using SSM agent 
    on given Instance and returns command ID
'''
def command_run(instance_id, script, command):

    print("command_run called")
    ssm = boto3.client('ssm', config=config)
    error = False

    try:
        response=ssm.send_command(
                Targets=[
                {
                    'Key': 'InstanceIds',
                    'Values': [instance_id]
                }],
                DocumentName=script,
                Comment='Selfheal_CS_restart',
                Parameters={'commands':command }
                )
        command_id = response['Command']['CommandId']
        
    except Exception as e:
        # print(PrintException())
        print("Error command_run() - ",e)
        print('Probably something is wrong with SSM connection :(')
        error = "Error command_run() - " + str(traceback.format_exc())
    finally:
        return command_id, error
        
    
'''
    This function returns the 
    status of the command ID
'''
def command_id_check(command_id,instance_id):

    print("command_id_check called")
    status = "False"
    error = False
    counter = 0
    try:
        while True:
            time.sleep(10)
            counter = counter + 1
            status1, error_status = command_status(command_id, instance_id)
            if not error_status:
                if not(status1 == 'InProgress'):
                    print("Status => "+ status1)
                    status = 'True'
                    break
                if counter == 18:
                    print("Probably SSM Connection Issue :(")
                    
            else:
                return status, error_status
        
    except Exception as e:
        # print(PrintException())
        print("Error command_id_check() - ",e)
        error = traceback.format_exc()
    
    return status, error
    
    
'''
    This function returns the 
    status of the command id
'''
def command_status(command_id, instance_id):

    print("command_status called")
    status = ""
    error_status = False
    try:
        s3 = boto3.client('ssm', config=config)
        response = s3.get_command_invocation(
            CommandId = command_id,
            InstanceId = instance_id,
        )
        status = response['Status']
        #print(response)
    except Exception as e:
        # print(PrintException())
        print("Error command_status() - ",e)
        error_status = traceback.format_exc()
        print("Something went wrong while checking the status of the Command ID")

    return status, error_status


'''
    This function returns the standard output 
    of the particular instance id in command id.
'''
def get_cmd_output(instance_id, command_id):

    print("get_cmd_output called")
    ssm = boto3.client('ssm', config=config)
    
    try:
        output = ssm.get_command_invocation(
                    CommandId=command_id,
                    InstanceId=instance_id,
                )

        #print(output)
        output_line = output['StandardOutputContent']
        error_line = output['StandardErrorContent']

        # if output_line == "":
        #     return error_line
        return output_line

    except Exception as e:
        # print(PrintException())
        print("Error get_cmd_output() - ",e)
        print("Error occur during get_command_invocation")

def lambda_handler(event,context):
    global task_token, instance_id

    print("Event Recieved: ", event)
    task_token = event['token']
    event = event["Payload"]
    instance_id = event["instance_id"]
    event["cs_restart_status_before_configure"] = "failed"

    input = {"resource_id" : event["instance_id"], "resource_type" : "EC2 Instance"}

    if event["ssm_ping_status"] == 'Online':
        
        if event["platform_type"] == "Linux":
            
            try:
                instance_id = event["instance_id"]

                if event["falcon_agent_status"] in ["installed_not_running", "installed_running"]:
                    script, command = cs_status_data(event)
                    command_id, error_status = command_run(instance_id, script, command)

                    if not error_status:
                        status, error = command_id_check(command_id,instance_id)
                        if not error:
                            if status:
                                output_1 = get_cmd_output(instance_id, command_id).split(";")[0]
                                print("output_1: ", output_1)
                            
                                if output_1 != "":
                                    script, command = cs_restart_data(event)
                                    command_id, error_status = command_run(instance_id, script, command)

                                    if not error_status:
                                        
                                        status, error = command_id_check(command_id,instance_id)
                                        if not error:
                                            if status:
                                                output_2 = get_cmd_output(instance_id, command_id).split(";")[0]
                                                print("output_2: ", output_2)
                                                
                                            if output_1 != output_2:
                                                event["cs_restart_status_before_configure"] = "success"

                                        else:
                                            print(f"Error during command_id_check() - {error}, returning restart status False")
                                    else:
                                        print(f"Error during command_run() - , returning restart status False")                       
                        else:
                            print(f"Error during command_id_check() - , returning restart status False")
                    else:
                        print(f"Error during command_run() - {error_status}, returning restart status False")

            except Exception as e:
                # print(PrintException())
                print("Error lambda_handler() - ",e) 
                input["error"] = f"Error lambda_handler() - {e}"
                err = traceback.format_exc()
                return failure_token(task_token, input, err)

            else:
                print(event)
                if event["cs_restart_status_before_configure"] == "failed":
                    event["falcon_agent_status"] = "not_installed"
                return success_token(event,task_token)
        else:
            if event["cs_restart_status_before_configure"] == "failed":
                event["falcon_agent_status"] = "not_installed"
            print("There is no solution to restart Windows CS Falcon Agent service")
            return success_token(event,task_token)
    else:
        if event["cs_restart_status_before_configure"] == "failed":
            event["falcon_agent_status"] = "not_installed"
        print("SSM_Ping_Status is not Online")
        return success_token(event,task_token)
        
    
event1 = {"instance_id":"i-0d5758a7ec1373272", "ssm_ping_status":"Online", "platform_type":"Linux", "falcon_agent_status":"installed_not_running"}
#   'i-011b47c2f1a5352cf'

if __name__ == "__main__":
    lambda_handler(event1,"")

