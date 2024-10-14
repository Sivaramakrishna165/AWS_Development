""" 
This Lambda function is used to check the status AWS CLI is installed or not.
If AWS CLI is installed shows as present,
If AWS CLI is not_installed shows as not_present.
and installs the CLI.

This Lambda is a part of Selfheal EC2 NativeBackupFailure

In Diagnosis state machine (dxcms_sh_nbf_sfn_diagnosis):
gets executed after - CheckSSM State
On successful check, next state - TriggerUnmountedVolCheck is called.
On FAILURE, next State - TriggerNotificationSfnWError and NotifyForLambaFunctionFailure.

In Resolution state machine (dxcms_sh_nbf_sfn_resolution):
gets executed after - CheckSSM
On successful check, next state - DynamoDbLogging is called.
On FAILURE, next State - TriggerNotificationSfnWError and NotifyForLambaFunctionFailure.
"""

from distutils.log import error
import json
import boto3
import time
import datetime
import os
import sys
import traceback
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


'''
    This function checks if the 
    CLI present or not
'''
def cli_check(instance_id):

    print("cli_check called")
    ssm = boto3.client('ssm', config=config)

    platform, error_status = platform_checker(instance_id)
    if not error_status:
        if platform == 'windows':
            script = "AWS-RunPowerShellScript"
        else:
            script = "AWS-RunShellScript"
        print('Using Script: '+ script)

        command = ['aws --version']
        command_id, error_status = command_run(instance_id, script, command)   
        print("Check CLI CMD_ID: ", command_id) 

        if not error_status:
            status = 'Not_Present'
            result, error_status = command_id_check(command_id,instance_id)
            if not error_status:
                try:
                    output = ssm.get_command_invocation(
                                CommandId=command_id,
                                InstanceId=instance_id,
                            )

                    #print(output)

                    output_line = output['StandardOutputContent']
                    error_line = output['StandardErrorContent']

                    if output_line.startswith('aws-cli/') or error_line.startswith('aws-cli/'):
                        print('Cli present')
                        status = 'Present'
                    else:
                        status = "Not_Present"
                except Exception as e:
                    # print(PrintException())
                    print(e)
                    error_status = traceback.format_exc()
                    print("Error occur during get_command_invocation")

    return status, error_status


def linux_type(instance_id):
    command = []
    ec2 = boto3.resource('ec2', config=config)
    try:
        inst_arch = ec2.Instance(instance_id).architecture
    except Exception as e:
        print("Error linux_type() - ",e)
    else:
        if inst_arch == 'arm64':
            command = [
                            "curl -O 'https://awscli.amazonaws.com/awscli-exe-linux-aarch64.zip'",
                            "sudo su",
                            "unzip -o awscli-exe-linux-aarch64.zip",
                            "sudo ./aws/install"
                        ]
        else:
            command = [
                            'curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64-2.0.30.zip" -o "awscliv2.zip"',
                            'sudo su',
                            'unzip -o awscliv2.zip',
                            'sudo ./aws/install'
                        ]
        return command


'''
    This function returns the appropriate Script 
    and Commands for a given instance ID
'''
def instance_data(instance_id):

    print("instance_data called")
    ssm = boto3.client('ssm', config=config)
    error = False
    os_command = {
                    'windows':  ['msiexec.exe /i https://awscli.amazonaws.com/AWSCLIV2.msi'],
                    'ubuntu':   [
                        'sudo apt update',
                        'sudo curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"',
                        'sudo apt install unzip',
                        'sudo unzip -o awscliv2.zip',
                        'sudo ./aws/install -i /usr/local/aws-cli -b /usr/local/bin'],  
                    'suse':     [
                        'sudo apt update',
                        'sudo curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"',
                        'sudo apt install unzip',
                        'sudo unzip -o awscliv2.zip',
                        'sudo ./aws/install -i /usr/local/aws-cli -b /usr/local/bin'], 
                    'sles':     [
                        'sudo apt update',
                        'sudo curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"',
                        'sudo apt install unzip',
                        'sudo unzip -o awscliv2.zip',
                        'sudo ./aws/install -i /usr/local/aws-cli -b /usr/local/bin'],
                    'debian':   [
                        'sudo apt update',
                        'sudo curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"',
                        'sudo apt install unzip',
                        'sudo unzip -o awscliv2.zip',
                        'sudo ./aws/install -i /usr/local/aws-cli -b /usr/local/bin'], 
                    'centos':   [
                        'sudo curl "https://s3.amazonaws.com/aws-cli/awscli-bundle-1.16.312.zip" -o "awscli-bundle.zip"',
                        'sudo yum makecache',
                        'sudo yum install unzip -y',
                        'sudo unzip -o awscli-bundle.zip',
                        'sudo ./awscli-bundle/install -i /usr/local/aws -b /usr/local/bin/aws'
                        ], 
                    'red hat':  [
                        # 'sudo yum update -y',
                        'sudo yum install unzip -y',
                        'sudo curl "https://s3.amazonaws.com/aws-cli/awscli-bundle-1.16.312.zip" -o "awscli-bundle.zip"',
                        'sudo unzip -o awscli-bundle.zip',
                        'sudo ./awscli-bundle/install -i /usr/local/aws -b /usr/local/bin/aws'
                        ], 
                    'oracle':[
                        'sudo yum install unzip -y',
                        'sudo rm -r aws',
                        'sudo curl "https://s3.amazonaws.com/aws-cli/awscli-bundle-1.16.312.zip" -o "awscli-bundle.zip"',
                        'sudo unzip -o awscli-bundle.zip',
                        'sudo ./awscli-bundle/install -i /usr/local/aws -b /usr/local/bin/aws'
                        ],
                    'linux': linux_type(instance_id) 
                }
    try:
        response = ssm.describe_instance_information(Filters=[{ 'Key': 'InstanceIds', 'Values': [instance_id]}])['InstanceInformationList'][0]
    except Exception as e:
        print("Error instance_data() - ",e)
        print('Probably something is wrong with SSM connection :(')
        return -1, -1
        
    else:

        print("P_Type: ",response['PlatformType'])
        print("P_Name: ",response['PlatformName'])

        script = "AWS-RunPowerShellScript" if response['PlatformType'].lower() == 'windows' else "AWS-RunShellScript"

        for key in os_command:
            if str(response['PlatformName']).lower().find(key) != -1:
                print(response['PlatformName'].lower())
                command = os_command[key]
                break
        
        return script, command
    
    
'''
    The function runs the command using SSM agent 
    on given Instance and returns command ID
'''
def command_run(instance_id, script, command):
    error = False
    print("command_run called")
    command_id = ""
    ssm = boto3.client('ssm', config=config)

    try:
        response=ssm.send_command(
                Targets=[
                {
                    'Key': 'InstanceIds',
                    'Values': [instance_id]       
                }],
                DocumentName=script,
                Comment='Selfheal_aws-cli',
                Parameters={'commands':command }
                )
        command_id = response['Command']['CommandId']
        
    except Exception as e:
        # print(PrintException())
        print("Error command_run() - ",e)
        error = traceback.format_exc()
        print('Probably something is wrong with SSM connection :(')
        
    return command_id, error


'''
    This function returns the 
    status of the command ID
'''
def command_id_check(command_id,instance_id):

    print("command_id_check called")
    status = "Not_Present"
    counter = 0
    error = False
    try:
        while True:
            time.sleep(10)
            counter = counter + 1
            status1, error = command_status(command_id, instance_id)
            if not error:
                if not(status1 == 'InProgress'):
                    print("Status => "+ status1)
                    if status1 == 'Success':
                        status = 'Present'
                    else:
                        status = 'Not_Present'
                    break
                if counter == 20:
                    print("Probably SSM Connection Issue :(")
                    break
    except:
        error = traceback.format_exc()
    
    return status, error


'''
    This function returns the 
    Platform of the instance
'''
def platform_checker(instance_id):

    print("platform_checker called")
    error = False
    ec2 = boto3.resource('ec2', config=config)
    
    try:
        instance = ec2.Instance(instance_id)
        platform = instance.platform
    except Exception as e:
        # print(PrintException())
        print("Error platform_checker() - ",e)
        error = traceback.format_exc()
        print("Something went wrong while checking the platform of Instance")
    
    #print(platform)

    return platform, error


'''
    This function returns the 
    status of the command 
'''
def command_status(command_id, instance_id):

    print("command_status called")
    error_status = False
    status = ""
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
    This function checks if particular key 
    is present or not with particular value
'''
def checkKey(dict, key, value):
    
    print("checkKey called")
    if key in dict.keys():
        if dict[key] == value:
            return True

    return False

def lambda_handler(event,context):
    global task_token, instance_id
    error_status = False
    print("Event Recieved: ", event)
    task_token = event['token']
    event = event["Payload"]
    instance_id = event["instance_id"]
    event["Instance_CLI_Status"] = "Not_Present"
    
    if event["SSM_Ping_Status"] == 'Online':
        
        try:   
            instance_id = event["instance_id"]
            
            status, error_status = cli_check(instance_id)
            if not error_status:
                if status == 'Present':
                    event["Instance_CLI_Status"] = status

                else:
                    if checkKey(event, "Flag", "Fix"):

                        print("Installing Cli.......")
                        script, command = instance_data(instance_id)

                        if str(script) != str(-1):
                            command_id, error_status = command_run(instance_id ,script, command)
                            print("CommandId: ", command_id)
                            if not error_status:
                                command_status, error_status = command_id_check(command_id,instance_id)
                                if not error_status:
                                    resultt, error_status = cli_check(instance_id)
                                    if not error_status:
                                        event["Instance_CLI_Status"] = resultt
                                    else:
                                        err = "Error during cli_check(instance_id)"
                                        return failure_token(task_token, err, error_status)
                                else:
                                    err = "Error command_id_check() - Error while checking status of command id."
                                    return failure_token(task_token, err, error_status)
                            else:
                                err = "Error during command_run(instance_id ,script, command)"
                                return failure_token(task_token, err, error_status)
                        else:
                            event["Instance_CLI_Status"] = status    
                    else:
                        event["Instance_CLI_Status"] = status

            else:
                return failure_token(task_token, "Error during cli_check(instance_id)", error_status)
                     
        except Exception as e:
            # print(PrintException())
            print("Error lambda_handler() - ",e)
            error_status = True
        
        if not error_status:    
            print(event)
            return success_token(event,task_token)
        else:
            return failure_token(task_token, "Error lambda handler()", error_status)
    else:
        print("SSM is not Online")   
        print(event)
        return success_token(event,task_token)
        
    
event1 = {"instance_id":"i-0d5758a7ec1373272", "SSM_Ping_Status":"Online", "Flag":"Fix"}
#   'i-011b47c2f1a5352cf'

if __name__ == "__main__":
    lambda_handler(event1,"")
