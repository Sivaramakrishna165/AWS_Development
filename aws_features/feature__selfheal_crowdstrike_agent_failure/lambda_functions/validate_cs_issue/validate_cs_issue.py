"""
    This Lambda function is used Validate Falcon_Agent_Status is installed or not.

    This Lambda is a part of Selfheal crowdstrike agent failure.
    In dxcms_sh_cs_sfn_resolution state machine(ValidateCSIssue)
    gets executed after InstallFalconAgent.

     Input event of the lambda function is:
     {
	"instance_id":"<instance-id>",
	"platform_type":"Windows/Linux"
    }

    In resolution state machine,
    On successful check, next state - Parallel State(SelfHealResolutionResult,StateMachineInfo) is called.
    On FAILURE, next State ValidateCSIssueError and then NotifyForLambaFunctionFailure.

"""


from distutils.log import error
import boto3
import json
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
        error = traceback.format_exc()
    
    return error

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
                Comment='Selfheal_aws-Falcon',
                Parameters={'commands':command }
                )
        command_id = response['Command']['CommandId']
        
    except Exception as e:
        print("Error command_run() - ",e)
        print('Probably something is wrong with SSM connection :(')
        error = traceback.format_exc()
        
    return command_id, error

def falcon_agent_validate(instance_id,platform):
    
    print("Falcon_agent_check called")
    status="not_installed"
    ssm = boto3.client('ssm', config=config)

    if platform == 'Windows':
        script = "AWS-RunPowerShellScript"
        command = ['sc.exe query csagent']
        command_id, error_status = command_run(instance_id, script, command)    
    else:
        script = "AWS-RunShellScript"
        command = ['sudo systemctl status falcon-sensor | grep Active']
        command_id, error_status = command_run(instance_id, script, command)  
    print('Using Script: '+ script)
    print("Check FalcoAagent CMD_ID: ", command_id)

    if not error_status:
        error_status = command_id_check(command_id,instance_id)
        if not error_status:
            try:
                output = ssm.get_command_invocation(
                            CommandId=command_id,
                            InstanceId=instance_id
                        )
                print(output)
                if platform == 'Windows':
                    if output['StandardOutputContent'] !="":
                        output_line = output['StandardOutputContent']
                        if "The specified service does not exist as an installed service" in output_line:
                            print('FalconAgent is not Installed')
                            status = "not_installed"
                        elif 'STATE              : 4  RUNNING' in output_line:
                            print('FalconAgent is Installed and running')
                            status = "installed_running"
                        else:
                            print('FalconAgent is Installed and Not_running')
                            status = "installed_not_running"
                    else:
                        print('FalconAgent is not Installed')
                        status = "not_installed"

                else:
                    if output['StandardOutputContent'] !="":
                        output_line = output['StandardOutputContent']
                        if output_line.startswith('     Active: active (running)') or output_line.startswith('   Active: active (running)') or output_line.startswith('    Active: active (running)'): 
                            status = 'installed_running'
                            print("installed and running")
                        elif output_line.startswith('   Active: inactive (dead)'):
                            print('Falconagent Installed and not running')
                            status = 'installed_not_running'
                        elif output_line.startswith('   Active: failed (Result: exit-code)'):
                            print("Installed and not_configured")
                            status = 'installed_not_configured'
                        else:
                            print('Falconagent not_installed')
                            status = 'not_installed'
                    else:
                        print('Falconagent not_installed')
                        status = "not_installed"
            except Exception as e:
                print("Error Falcon_agent_check() - ",e)
                print("Error occur during get_command_invocation")
                error_status = traceback.format_exc()
        else:
            error_status = f"Error command_id_check() - Something is wrong with run command id {command_id}" + str(error_status)
    else:
        error_status = "Error command_run() - Unable to send command" + str(error_status)

    return  status, error_status

def get_ssm_status(instance_id):
    Instance_SSM_Status = 'Not_Present'
    SSM_Agent_Version = 'Not_Present'
    Ping_Status = 'Connection_Lost'
    ssm_error = ""
    try:
        ssm_client = boto3.client('ssm',config=config)
        response = ssm_client.describe_instance_information(
            InstanceInformationFilterList=[
                { 'key': 'InstanceIds', 'valueSet': [ instance_id, ] },
            ],
        )
        if response['InstanceInformationList']:
            Instance_SSM_Status = 'Present'
            SSM_Agent_Version = response['InstanceInformationList'][0]['AgentVersion']
            Ping_Status = response['InstanceInformationList'][0]['PingStatus']
        
    except Exception as e:
        print("Error get_ssm_status() - ",e)
        ssm_error = traceback.format_exc()

    return Instance_SSM_Status, SSM_Agent_Version, Ping_Status, ssm_error

def lambda_handler(event,context):
    global task_token, instance_id
    print("Received Event is :",event)
    error_status = False
    task_token = event['token']
    event = event["Payload"]
    instance_id = event["instance_id"]
    event['ssm_ping_status'] = 'offline'
    event["falcon_agent_status"] = "not_installed"
    
    try:
        ssm_ping_status, SSM_Agent_Version, Ping_Status, ssm_error = get_ssm_status(instance_id)

        if not ssm_error:
            if ssm_ping_status == 'Present':
                event['ssm_ping_status'] = 'online'
                platform = event["platform_type"]
                status, error_status = falcon_agent_validate(instance_id,platform)
                if not error_status:
                    event["falcon_agent_status"] = status
                else:
                    print(f"Error while validating falcon agent status - {error_status}")
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
        if not error_status:
            error_status = traceback.format_exc()
        return failure_token(task_token, input, error_status)