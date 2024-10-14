"""
    This Lambda function is used to check the status of CW_agent installed 
    and configured.

    This Lambda is a part of Selfheal cloudwatch agent failure.
    In dxcms_sh_cw_sfn_diagnosis state machine(CheckCWAgentDetails),
    gets executed after FetchInstanceDetails step.
    Input event of the lambda function is:
        {
            "instance_id":"<instance_id>", 
            "platform_type":"Windows"
        }
    instance = running.
    In Diagnosis state machine,
    On successful check, next state -selfhealdiagnosis result and statemachineinfo is called.
    On FAILURE, next State CheckCWAgentDetailsError and then NotifyForLambaFunctionFailure.

"""

import json
import boto3
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

def command_id_check(command_id,instance_id):
    
    print("command_id_check called")
    error = False
    try:
        ssm = boto3.client('ssm', config=config)
        waiter = ssm.get_waiter('command_executed')
        waiter.wait(
            CommandId=command_id,
            InstanceId=instance_id,
            WaiterConfig={
                'Delay': 5,
                'MaxAttempts': 25
            }
        )
    except Exception as e:
        print("Error command_id_check() - ",e)
        error = True
    
    return  error

def command_run(instance_id, script, command):
    error = False
    command_id=""
    print("command_run called")
    ssm = boto3.client('ssm', config=config)

    try:
        response=ssm.send_command(
                Targets=[
                {
                    'Key': 'InstanceIds',
                    'Values': [instance_id]       
                }],
                DocumentName=script,
                Comment='Selfheal_aws',
                Parameters={'commands':command }
                )
        command_id = response['Command']['CommandId']
        
    except Exception as e:
        print("Error command_run() - ",e)
        error = True
        print('Probably something is wrong with SSM connection :()')
        
    return command_id, error


def cw_config_check(instance_id,platform):
    
    print("CW_config_check called")
    agent_status = 'not_installed'
    config_status = 'not_configured'
    ssm = boto3.client('ssm', config=config)

    if platform == 'Windows':
        script = "AWS-RunPowerShellScript"
        
        command = ['&  C:\\"Program Files"\\Amazon\AmazonCloudWatchAgent\\amazon-cloudwatch-agent-ctl.ps1 -m ec2 -a status']

        command_id, error_status = command_run(instance_id, script, command)    
    else:
        script = "AWS-RunShellScript"
        
        command = ['sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -m ec2 -a status']
        
        command_id, error_status = command_run(instance_id, script, command)  
    print('Using Script: '+ script)

    print("Check CWagent CMD_ID: ", command_id) 
    

    if not error_status:
        error_status = command_id_check(command_id,instance_id)
        if not error_status:
            try:
                output = ssm.get_command_invocation(
                            CommandId=command_id,
                            InstanceId=instance_id,
                        )
                print(output)
                
                if output['StandardOutputContent'] !="":
                    output_line = output['StandardOutputContent']
                    res = json.loads(output_line)

                    if res["status"]=="running" and res["configstatus"] == "configured":
                        print('CWagent installed')
                        print("Config file is configured")
                        agent_status = 'installed_and_running'
                        config_status = 'configured'
                    elif res["status"]=="stopped" and res["configstatus"] == "not configured":
                        print('CWagent installed')
                        print("Config file is Not_configured")
                        agent_status = 'installed'
                        config_status = 'not_configured'
                    elif res["status"]=="stopped" and res["configstatus"] == "configured":
                        print('CWagent installed and need to restart')
                        print("Config file is configured")
                        agent_status = 'installed_and_not_running'
                        config_status = 'configured'
                else:
                    print('CWagent Not_present')
                    print("Config file is Not_configured")
                    agent_status = 'not_installed'
                    config_status = 'not_configured'
                    
            except Exception as e:
                print("Error cw_agent_check() - ",e)
                error_status = True
                print("Error occur during get_command_invocation")
   
    return  agent_status, config_status, error_status

def get_ssm_status(instance_id):
    Instance_SSM_Status = 'Not_Present'
    ssm_error = False
    try:
        ssm_client = boto3.client('ssm',config=config)
        response = ssm_client.describe_instance_information(
            InstanceInformationFilterList=[
                { 'key': 'InstanceIds', 'valueSet': [ instance_id, ] },
            ],
        )
        if response['InstanceInformationList']:
            Instance_SSM_Status = 'Present'
    except Exception as e:
        print("Error get_ssm_status() - ",e)
        Instance_SSM_Status = 'Not_Present'
        ssm_error = traceback.format_exc()
    finally:
        return Instance_SSM_Status, ssm_error

def lambda_handler(event,context):
    global task_token, instance_id
    print("Received Event is :",event)
    error_status = False
    task_token = event['token']
    event = event["Payload"]

    event['ssm_ping_status'] = 'Offline'
    event["cw_agent_status"] = "not_installed"
    event["configfile_status"] = "not_configured"
    
    instance_id = event["instance_id"]
        
    try:
        Instance_SSM_Status, ssm_error = get_ssm_status(instance_id)
        if not ssm_error:
            if Instance_SSM_Status == 'Present':
                event['ssm_ping_status'] = 'online'
                platform = event["platform_type"]
                agent_status, config_status, error_status = cw_config_check(instance_id,platform)
                if not error_status:
                    event["cw_agent_status"] = agent_status
                    event["configfile_status"] = config_status
                    print(event)
            else:
                print("SSM is not Online")   
                print(event)
        else:
            err = "Error while checking ssm connection"
            input = {"error" : str(err), "resource_id" : instance_id, "resource_type" : "EC2 Instance"}
            return failure_token(task_token, input, ssm_error)
        return success_token(event,task_token)
    except Exception as e:
        print("Error lambda_handler() - ",e)
        err = f"Error lambda_handler() - {str(e)}"
        input = {"error" : str(err), "resource_id" : instance_id, "resource_type" : "EC2 Instance"}
        return failure_token(task_token, input, traceback.format_exc())