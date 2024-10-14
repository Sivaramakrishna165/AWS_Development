"""
    This Lambda function is used to install CWagent and to configure the 
    config file.

    This Lambda is a part of Selfheal cloudwatch agent failure.
    In dxcms_sh_cw_sfn_resolution state machine(ReConfigureCWAgent),
    gets executed after ChoiceCWInstallation.
    Input event of the lambda function is:
        {
            "instance_id":"<instance_id>",
            "cw_agent_status":"not_installed/installed/installed_and_not_running",
            "configfile_status":"not_configured/configured",
            "platform_type":"Windows/Linux"
        }
    instance = running.
    In resolution state machine,
    On successful check, next state - WaitForValidation is called.
    On FAILURE, next State ReConfigureCWAgentError and then NotifyForLambaFunctionFailure.

"""

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
        error = True
    
    return  error

def command_run(instance_id,Document_Name,Comment_Name,parameters_list):
    error = False
    print("command_run called")
    ssm = boto3.client('ssm', config=config)

    try:
        print('instance is:',instance_id)
        print("Document name is :",Document_Name)
        print("Comment_Name is :",Comment_Name)
        print("parameters_list is :",parameters_list)
        response=ssm.send_command(
                Targets=[
                {
                    'Key': 'InstanceIds',
                    'Values': [instance_id]       
                }],
                DocumentName=Document_Name,
                Comment=Comment_Name,
                Parameters=parameters_list
                )

        command_id = response['Command']['CommandId']
        
        
    except Exception as e:
        print("Error command_run() - ",e)
        error = True
        print('Probably something is wrong with SSM connection :(')
        
    return command_id, error


def fix_cw_config(count,instance_id,platform):
    
    print("Fixing_the_issue")
    config_status = 'not_configured'
    cw_agent_status = "not_installed"
    
    ssm = boto3.client('ssm', config=config)

    if platform=='Windows':
        ssm="/DXC/AWS-CWAgentWinConfig"
        if count == 1:
            Document_Name="AWS-RunPowerShellScript"
            Comment_Name="Restarting the agent"
            parameters_list={
                'commands':['Restart-Service AmazonCloudWatchAgent']
                }
    else:
        ssm="/DXC/AWS-CWAgentConfig"
        if count == 1:
            Document_Name="AWS-RunShellScript"
            Comment_Name="Restarting the agent"
            parameters_list={
                "commands":['sudo systemctl restart amazon-cloudwatch-agent.service']
                }
        
    if count==2 or count==4:
        Document_Name="AmazonCloudWatch-ManageAgent"
        Comment_Name='Configuration with Agent'
        parameters_list={
                    "action":["configure"],
                    "mode":["ec2"],
                    "optionalConfigurationLocation":[ssm],
                    "optionalConfigurationSource":["ssm"],
                    # "optionalOpenTelemetryCollectorConfigurationLocation":[""],
                    # "optionalOpenTelemetryCollectorConfigurationSource":["ssm"],
                    "optionalRestart":["yes"]
                }

    elif count==3:
        Document_Name="AWS-ConfigureAWSPackage"
        Comment_Name='Install or uninstall a Distributor package.'
        parameters_list={ 
            "action":["Install"],
            "installationType":["Uninstall and reinstall"],
            "name":["AmazonCloudWatchAgent"],
            "additionalArguments":["{}"]
        }
            
    command_id, error_status = command_run(instance_id,Document_Name,Comment_Name,parameters_list)  

    print("Check CWagent CMD_ID: ", command_id) 
    

    if not error_status:
        error_status = command_id_check(command_id,instance_id)
        if not error_status:
            print("command_id : ",command_id)
            print("instance_id is ",instance_id)

            cw_agent_status = "installed_and_running"
            config_status = "configured"


    return cw_agent_status,config_status,error_status

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
    event['ssm_ping_status'] = 'offline'
    instance_id = event["instance_id"]

    count=0
    try:
        Instance_SSM_Status, ssm_error = get_ssm_status(instance_id)
        if not ssm_error:
            if Instance_SSM_Status == 'Present':
                event['ssm_ping_status'] = 'online'
                platform=event["platform_type"]
                if event["cw_agent_status"] == "installed" and event["configfile_status"] == "not_configured":
                    count=2
                    cw_agent_status,config_status, error_status = fix_cw_config(count,instance_id,platform)
                    if not error_status:
                        event["configfile_status"] = config_status
                        event["cw_agent_status"] = cw_agent_status
                    else:
                        print(f"Error while configuring cloudwatch agent - {str(error_status)}")
                    print(event)
                elif (event["cw_agent_status"] == 'installed_and_not_running' and event["configfile_status"] == 'configured') or (event["cw_agent_status"] == "not_installed" and event["configfile_status"] == "not_configured"):
                    count=3
                    cw_agent_status, config_status, error_status = fix_cw_config(count,instance_id,platform)
                    if not error_status:
                        count=4
                        event["cw_agent_status"] = cw_agent_status
                        cw_agent_status, config_status, error_status = fix_cw_config(count,instance_id,platform)
                        if not error_status:
                            event["configfile_status"] = config_status
                    print(event)
                else:
                    print(event)
            else:
                print("SSM is not online")   
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