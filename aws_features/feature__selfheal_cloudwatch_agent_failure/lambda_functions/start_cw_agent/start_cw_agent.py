"""
    This Lambda function is used to restart the Cloud Watch Agent 
    and returns the restart status as success or failed.

    This Lambda is a part of Selfheal cloudwatch agent failure.
    In dxcms_sh_cw_sfn_resolution state machine(RestartCWAgent)
    gets executed after FetchINstanceDetails Step.

    Input event of the lambda function is:
    {
        "instance_id":"<instance_id>", 
        "ssm_ping_status":"Online", 
        "cw_agent_status": "Installed_and_not_running", 
        "configfile_status": "Configured", 
        "platform_type": "Linux/Windows"
    }

    In Resolution state machine,
    On successful check, next state - ChoiceRestartValidation is called.
    On FAILURE, next State RestartCWAgentError and then NotifyForLambaFunctionFailure

"""

import json
import boto3
import sys
import time
import traceback
from datetime import datetime, timezone
from botocore.config import Config


config=Config(retries=dict(max_attempts=10,mode='standard'))


# '''
#     This function will return the Line 
#     number and the error that occured.
# '''
# def PrintException():
#     exc_type, exc_obj, tb = sys.exc_info()
#     f = tb.tb_frame
#     lineno = tb.tb_lineno
#     captureErr = "Line No. : " + str(lineno)  + " | ERROR: " + str(exc_obj)
#     return captureErr


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
            error = str(error),
            cause = cause
        )
        print('failure task token sent - ',sf_response)
    except Exception as e:
        print("Error failure_token() - ", e)
        raise


def cw_status_data(event):
    print("cw_restart_data called")

    if event["platform_type"] == "Windows":
        script = "AWS-RunPowerShellScript"
        command = [r'C:\\"Program Files"\\Amazon\AmazonCloudWatchAgent\\amazon-cloudwatch-agent-ctl.ps1 -m ec2 -a status']
    else:
        script = "AWS-RunShellScript"
        command = ["sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -m ec2 -a status"]

    return script, command


def cw_restart_data(event):
    print("cw_restart_data called")

    if event["platform_type"] == "Windows":
        script = "AWS-RunPowerShellScript"
        command = [
                    "Restart-Service AmazonCloudWatchAgent",
                    r'C:\\"Program Files"\\Amazon\AmazonCloudWatchAgent\\amazon-cloudwatch-agent-ctl.ps1 -m ec2 -a status'
                ]
    else:
        script = "AWS-RunShellScript"
        command = [
                    "sudo systemctl restart amazon-cloudwatch-agent",
                    "sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -m ec2 -a status"
                ]

    return script, command


'''
    The function runs the command using SSM agent 
    on given Instance and returns command ID
'''
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
    status of the command 
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
        # print("output_line:" ,output_line == '')
        error_line = output['StandardErrorContent']
        if output_line == '':
            return "{}"
        return output_line

    except Exception as e:
        # print(PrintException())
        print("Error get_cmd_output() - ",e)
        print("Error occur during get_command_invocation")


# def token(event, task_token):

#     sf = boto3.client('stepfunctions')
#     sf_output = json.dumps(event)
#     # task_token = event['token']

#     sf_response = sf.send_task_success(
#         taskToken=task_token,
#         output=str(sf_output)
#     )

#     return sf_response


def lambda_handler(event,context):
    
    print("Event Recieved: ", event)
    task_token = event['token']
    event = event["Payload"]
    input = {"resource_id" : event["instance_id"], "resource_type" : "EC2 Instance"}
    event["time_stamp"] = int((datetime.now(timezone.utc)).timestamp()*1000)
    event["cw_restart_status_before_configure"] = "failed"

    if event["ssm_ping_status"] == 'Online':
        if (event["cw_agent_status"] in ['installed_and_not_running', 'installed_and_running']) and event["configfile_status"] == 'configured':
            output_1 = " "
            try:
                
                instance_id = event["instance_id"]
                script, command = cw_status_data(event)
                command_id, error_status = command_run(instance_id, script, command)
                if not error_status:
                    status, error = command_id_check(command_id,instance_id)
                    if not error:
                        if status:
                            output_1 = json.loads(get_cmd_output(instance_id, command_id))
                            print("output_1: ", output_1)
                        if output_1:
                            # event["agent_status"] = "Installed"
                            script, command = cw_restart_data(event)
                            command_id, error_status = command_run(instance_id, script, command)
                
                            if not error_status:
                                status, error_2 = command_id_check(command_id,instance_id)

                                if not error_2:

                                    if status:
                                        output_2 = json.loads(get_cmd_output(instance_id, command_id))
                                        print("output_2: ", output_2)
                                        
                                    if output_1['starttime'] != output_2['starttime']:
                                        event["cw_restart_status_before_configure"] = "success"

                                else:
                                    print(f"Error during command_id_check() - {error_2}, returning restart status False")
                                    input["error"] = f"Error during command_id_check() - {error_status}, returning restart status False"
                                    return failure_token(task_token, input, e)
                                
                            else:
                                print(f"Error during command_run() - , returning restart status False") 
                                input["error"] = f"Error during command_run() - , returning restart status False"
                                return failure_token(task_token, input, e)


                    else:
                        print(f"Error during command_id_check() - {error_status}, returning restart status False")
                        input["error"] = f"Error during command_id_check() - {error_status}, returning restart status False"
                        return failure_token(task_token, input, e)
                

                else:
                    print(f"Error during command_run() - , returning restart status False") 
                    input["error"] = f"Error during command_run() - , returning restart status False"
                    return failure_token(task_token, input, e)
                                    
                                    # event["CWagent_Status"] = 'Installed_and_running'
                                # else:
                                #     event["CWagent_Status"] = "Not_Installed"
                                #     event["Configfile_Status"] = "Not_Configured"
                                # event["agent_status"] = "Not_Installed"
                    
            except Exception as e:
                # print(PrintException())
                print("Error lambda_handler() - ",e)
                input["error"] = "Something Went Wrong"
                return failure_token(task_token, input, e)
            else:
                print(event)
                return success_token(event, task_token)
    else:
        print("SSM_Ping_Status is not Online")

    # event["CWagent_Status"] = "Not_Installed"
    # event["Configfile_Status"] = "Not_Configured"   
    return success_token(event, task_token)
        
    
event1 = {"instance_id":"i-0d5758a7ec1373272", "ssm_ping_status":"Online", "cw_agent_status": "Installed_and_not_running", "configfile_status": "Configured", "platform_type": "Linux"}
#   'i-011b47c2f1a5352cf'

if __name__ == "__main__":
    lambda_handler(event1,"")

