"""
    This Lambda function is used to install the falcon agent.

    This Lambda is a part of Selfheal crowdstrike agent failure.
    In dxcms_sh_cs_sfn_resolution state machine(InstallFalconAgent)
    gets executed after ChoiceRestartValidation to install falcon agent.

    Input event of the lambda function is:
    {
	"instance_id":"<instance_id>",
	"falcon_agent_status":"not_installed/installed_not_running",
	"os_flavour":"windows/oracle/ubuntu/sles/red hat/amazon",
	"instance_cli_status":"present"
    }

    In resolution state machine,
    On successful check, next state ValidateCSIssue is called.
    On FAILURE, next State InstallFalconAgentError and then NotifyForLambaFunctionFailure.

"""


from distutils.log import error
import boto3
import os
import json
import traceback
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))
s3_bucket = os.environ['s3_bucket']
crowdstrike_CID = os.environ['crowdstrike_CID']

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
                'MaxAttempts': 72
            }
        )
    except Exception as e:
        print("Error occured because of the AMI Version no falcon agent package for this AMI version")
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

def fix_agent_check(count,instance_id,platform,bucket,customer_id):
    error_status = False
    print("Falcon_agent_fixing")
    status="not_installed"
    ssm = boto3.client('ssm', config=config)
    if count == 1:
        if platform == 'windows':
            script = "AWS-RunPowerShellScript"
            command = ["Start-Service CsFalconService "]
        else:
            script = "AWS-RunShellScript"
            command = ["sudo systemctl start falcon-sensor.service"]
    elif count == 2:
        if platform != 'windows':
            script = "AWS-RunShellScript"
            command = [
                f"sudo /opt/CrowdStrike/falconctl -s -f --cid={customer_id}",
                "sudo systemctl start falcon-sensor"
                ]
    elif count == 3:
        if platform == 'windows':
            region = os.environ['AWS_REGION']
            script = "AWS-RunPowerShellScript"
            command = [
            "Set-Variable -Name \"crowdStrikeExe\" -Value \"WindowsSensor.exe\"",
            "Get-Variable -Name \"crowdStrikeExe\"", 
            f"Set-Variable -Name \"BUCKET\" -Value {bucket} ",
            "Get-Variable -Name \"BUCKET\" ",
            f"Set-Variable -Name \"REGIONNAME\" -Value {region} ",
            "Get-Variable -Name \"REGIONNAME\" ",
            "Read-S3Object -BucketName $BUCKET -key deploy/externs/windows/$crowdStrikeExe -Region $REGIONNAME -File c:\Temp\$crowdStrikeExe  ",
            "cd c:\Temp ",
            f"Set-Variable -Name \"installer\" -Value \".\$crowdStrikeExe /install /quiet /norestart CID={customer_id}\" ",
            "Get-Variable -Name \"installer\"",
            "Invoke-Expression -Command $installer ",
            "get-service | findstr /i /r \"Running.*CrowdStrike\""
            ]
        elif platform == "amazon":
            script = "AWS-RunShellScript"
            command = ["if [ \"true\" ==  \"true\"  ]; then",
                        ". /etc/os-release",
                        "VERSION_ID=$(cut -d'.' -f1 <<<$VERSION_ID)",
                        "echo \"Version is $VERSION_ID   \"",
                        "OSARCH=`uname -m`",
                        "echo \"OSARCH: $OSARCH\"",
                        "if [ \"$OSARCH\" == \"aarch64\" ]; then   sub_folder=\"$VERSION_ID - arm64\"",
                        "elif [ \"$OSARCH\" == \"x86_64\" ]; then   sub_folder=\"$VERSION_ID\"",
                        "else  die \"Could not identify OS architecture.\"",
                        "fi",
                        "echo \"sub_folder is $sub_folder   \"",
                        f"BUCKET={bucket}",
                        "echo \"BUCKET is $BUCKET\"",
                        "FALCON=`aws s3 ls \"s3://$BUCKET/deploy/externs/linux/amazon-linux/$sub_folder/\"  --recursive  | sort | tail -n 1 | sed 's/^[   ]*//' | cut -d\"/\" -f6-`",
                        "echo \"FALCON:$FALCON\"",
                        "if [[ -z $FALCON ]]; then",
                                "echo \"No $FALCON file found in $BUCKET/deploy/externs/linux/amazon-linux/$sub_folder\"",
                            "else",
                                "aws s3 cp \"s3://$BUCKET/deploy/externs/linux/amazon-linux/$sub_folder/$FALCON\" /tmp/",
                                "if [[ $? -ne 0 ]]; then",
                                    "echo \"Issue copying $FALCON file to host.\"",
                                "else",
                                    "echo \"$FALCON file moved to instance.\"",
                                    "sudo yum install -y libnl-1.1.4",
                                    "sudo yum install policycoreutils-python -y",
                                    "sudo rpm -Uvh /tmp/$FALCON",
                                "fi",
                            "fi",
                        "else",
                        "echo \"ApplyEndpointProtection is set to False\"",
                        "fi",
                        f"sudo /opt/CrowdStrike/falconctl -s -f --cid={customer_id}",
                        "sudo systemctl start falcon-sensor"
                        ]
                    
        elif platform == "ubuntu":
            script = "AWS-RunShellScript"
            command = [
                    ". /etc/os-release",
                    "VERSION_ID=$VERSION_ID",
                    "echo \"version is $VERSION_ID\"",
                    "VERSION_ID=$(printf \%\.0f $VERSION_ID)",
                    "echo \"version is $VERSION_ID\"",
                    f"BUCKET={bucket}",
                    "echo \"BUCKET is $BUCKET\"",
                    "FALCON=`aws s3 ls \"s3://$BUCKET/deploy/externs/linux/ubuntu/$VERSION_ID/\"  --recursive  | sort | tail -n 1 | sed 's/^[   ]*//' | cut -d\"/\" -f6-`",
                    "echo \"FALCON:$FALCON\"",
                    "if [[ -z $FALCON ]]; then",
                        "echo \"No $FALCON file found in $BUCKET/deploy/externs/linux/ubuntu/$VERSION_ID\"",
                    "else",
                        "aws s3 cp \"s3://$BUCKET/deploy/externs/linux/ubuntu/$VERSION_ID/$FALCON\" /tmp/",
                        "sudo apt install /tmp/$FALCON -y",
                    "fi",
                    f"sudo /opt/CrowdStrike/falconctl -s -f --cid={customer_id}",
                    "sudo systemctl start falcon-sensor"
            ]
        elif platform == "sles":
            script = "AWS-RunShellScript"
            command = [ 
            ". /etc/os-release ",
            "VERSION_ID=$VERSION_ID",
            "echo \"version is $VERSION_ID\"",
            "VERSION_ID=$(printf %.0f $VERSION_ID)",
            "echo \"version is $VERSION_ID\"",
            f"BUCKET={bucket}",
            "echo \"BUCKET is $BUCKET\"",
            "FALCON=`aws s3 ls \"s3://$BUCKET/deploy/externs/linux/sles/$VERSION_ID/\"  --recursive  | sort | tail -n 1 | sed 's/^[   ]*//' | cut -d\"/\" -f6-`",
            "echo \"FALCON:$FALCON\"",
            "if [[ -z $FALCON ]]; then",
                "echo \"No $FALCON file found in $BUCKET/deploy/externs/linux/sles/$VERSION_ID\"",
            "else",
                "aws s3 cp \"s3://$BUCKET/deploy/externs/linux/sles/$VERSION_ID/$FALCON\" /tmp/$FALCON",
                "if [[ $? -ne 0 ]]; then",
                    "echo \"Issue copying $FALCON file to host.\";",
                "else",
                    "echo \"$FALCON file moved to instance.\"",
                    "sudo zypper -n install policycoreutils-python",
                    "sudo rpm -Uvh /tmp/$FALCON",
                "fi",
            "fi",
            f"sudo /opt/CrowdStrike/falconctl -s -f --cid={customer_id}",
            "sudo systemctl start falcon-sensor"
            ]
        elif platform == "red hat":
            script = "AWS-RunShellScript"
            command = [
            ". /etc/os-release ",
            "VERSION_ID=$VERSION_ID",
            "echo \"version is $VERSION_ID\"",
            "VERSION_ID=$(printf \%.\0f $VERSION_ID)",
            "echo \"version is $VERSION_ID\"",
            f"BUCKET={bucket}",
            "echo \"BUCKET is $BUCKET\"",
            "FALCON=`aws s3 ls \"s3://$BUCKET/deploy/externs/linux/rhel/$VERSION_ID/\"  --recursive  | sort | tail -n 1 | sed 's/^[   ]*//' | cut -d\"/\" -f6-`",
            "echo \"FALCON:$FALCON\"",
            "if [[ -z $FALCON ]]; then",
                "echo \"No $FALCON file found in $BUCKET/deploy/externs/linux/rhel/$VERSION_ID\"",
            "else",
                "aws s3 cp \"s3://$BUCKET/deploy/externs/linux/rhel/$VERSION_ID/$FALCON\" /tmp/$FALCON",
                "if [[ $? -ne 0 ]]; then",
                    "echo \"Issue copying $FALCON file to host.\";",
                "else",
                    "echo \"$FALCON file moved to instance.\"",
                    "sudo rpm -Uvh /tmp/$FALCON",
                "fi",
            "fi",
            f"sudo /opt/CrowdStrike/falconctl -s -f --cid={customer_id}",
            "sudo systemctl start falcon-sensor"
            ]
        elif platform == "oracle":
            script = "AWS-RunShellScript"
            command = [
                ". /etc/os-release",
                "VERSION_ID=$(cut -d'.' -f1 <<<$VERSION_ID)",
                "echo \"Verion is $VERSION_ID\"",
#                 ". /etc/os-release ",
#                 "VERSION_ID=$VERSION_ID",
#                 "echo \"version is $VERSION_ID\"",
#                 "VERSION_ID=$(printf \%.\0f $VERSION_ID)",
#                 "echo \"version is $VERSION_ID\"",
                f"BUCKET={bucket}",
                "echo \"BUCKET is $BUCKET\"",
                "FALCON=`aws s3 ls \"s3://$BUCKET/deploy/externs/linux/oracle/$VERSION_ID/\"  --recursive  | sort | tail -n 1 | sed 's/^[   ]*//' | cut -d\"/\" -f6-`",
                "echo \"FALCON:$FALCON\"",
                "if [[ -z $FALCON ]]; then",
                    "echo \"No $FALCON file found in $BUCKET/deploy/externs/linux/oracle/$VERSION_ID\"",
                "else",
                    "aws s3 cp \"s3://$BUCKET/deploy/externs/linux/oracle/$VERSION_ID/$FALCON\" /tmp/$FALCON",
                    "if [[ $? -ne 0 ]]; then",
                        "echo \"Issue copying $FALCON file to host.\";",
                    "else",
                        "echo \"$FALCON file moved to instance.\"",
                        "sudo yum install -y libnl-1.1.4",
                        "sudo yum install policycoreutils-python -y",
                        "sudo rpm -Uvh /tmp/$FALCON",
                    "fi",
                "fi",
                f"sudo /opt/CrowdStrike/falconctl -s -f --cid={customer_id}",
                "sudo systemctl start falcon-sensor"
            ]
        else:
            print("Platform type is not found under this ['windows', 'oracle', 'ubuntu', 'sles', 'red hat', 'amazon']")
            error_status= "Platform type is not found under this ['windows', 'oracle', 'ubuntu', 'sles', 'red hat', 'amazon']"
    if not error_status:
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
                if platform == 'windows':
                    if output['Status'] == "Success":
                        if output['StandardErrorContent'] == "":
                            status = 'installed_running'
                            print('Falconagent Installed and running')
                        else:
                            status = "not_installed"
                            print('Falconagent not_installed')
                            
                    else:
                        print('Falconagent not_installed')
                        status = "not_installed"
                else:
                    if output['Status'] == "Success":
                       status = 'installed_running'
                       print('Falconagent Installed and running')
                    else:
                        print('Falconagent not_installed')
                        status = "not_installed"
            except Exception as e:
                print("Error Falcon_agent_check() - ",e)
                print("Error occur during get_command_invocation")
                error_status = traceback.format_exc()
        else:
            error_status = "Error command_id_check - Maybe no falcon agent package for this AMI version" + str(error_status)
    else:
        error_status = "Error command_run() - Error while send command" + str(error_status)

    return  status, error_status

def ssm_parameter(name):
    error_status = ""
    try:
        ssm = boto3.client('ssm',config=config)
        response = ssm.get_parameter(
            Name = name,
            WithDecryption=True
        )
        result=response['Parameter']['Value']
    except Exception as e:
        print("error in ssm parameter",e)
        error_status = traceback.format_exc()
        result = None
    return result,error_status

def get_ssm_status(instance_id):
    Instance_SSM_Status = 'offline'
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
            Instance_SSM_Status = 'Online'
            SSM_Agent_Version = response['InstanceInformationList'][0]['AgentVersion']
            Ping_Status = response['InstanceInformationList'][0]['PingStatus']
        
    except Exception as e:
        print("Error get_ssm_status() - ",e)
        ssm_error = traceback.format_exc()

    return Instance_SSM_Status, SSM_Agent_Version, Ping_Status, ssm_error

def lambda_handler(event,context):
    global task_token, instance_id
    print("Received Event is :",event)
    error_status = ""
    task_token = event['token']
    event = event["Payload"]
    instance_id = event["instance_id"]
    count=0    
    event['ssm_ping_status'] = 'offline'
    falcon_agent_status = event["falcon_agent_status"]
    instance_cli_status = event["instance_cli_status"]
 
    try:
        ssm_ping_status, SSM_Agent_Version, Ping_Status, ssm_error = get_ssm_status(instance_id)
        event['ssm_ping_status']  = ssm_ping_status
        if event["cs_restart_status_before_configure"] == "success":
            event["falcon_agent_status"] = 'installed_running'
        else:
            if not ssm_error:
                if ssm_ping_status == 'Online':
                    platformtype = event["platform_type"] 
                    if platformtype == "Windows" or (instance_cli_status == 'present' and platformtype == "Linux"): 
                        platform=event["os_flavour"]
                        bucket,s3_error_status = ssm_parameter(s3_bucket)
                        print('bucket is : ',bucket)
                        CID,cid_error_status = ssm_parameter(crowdstrike_CID)
                        if CID.startswith('CID-'):
                            crowdstrikeID = CID[4:]
                        else:
                            crowdstrikeID=CID
                
                        if not s3_error_status and not cid_error_status:
                            # if falcon_agent_status == 'installed_not_running':
                            #     count = 1
                            #     status, error_status = fix_agent_check(count,instance_id,platform,bucket,customer_id)
                            #     if not error_status:
                            #         event["falcon_agent_status"] = status
                            if falcon_agent_status == 'installed_not_configured':
                                count = 2
                                status, error_status = fix_agent_check(count,instance_id,platform,bucket,crowdstrikeID)
                                if not error_status:
                                    event["falcon_agent_status"] = status
                                else:
                                    print(f"Error while fixing falcon agent - {str(error_status)}")
                            elif (falcon_agent_status == 'installed_not_running') or (falcon_agent_status == 'not_installed'):
                                count = 3
                                status, error_status = fix_agent_check(count,instance_id,platform,bucket,crowdstrikeID)
                                if not error_status:
                                    event["falcon_agent_status"] = status
                                else:
                                    print(f"Error while fixing falcon agent - {str(error_status)}")
                            print(event)
                        else:
                            print("Error while fetching data from ssm")
                            if s3_error_status:
                                err = f"Error while reading ssm parameter {s3_bucket}"
                                input = {"error" : str(err), "resource_id" : instance_id, "resource_type" : "EC2 Instance"}
                                return failure_token(task_token, input, s3_error_status)
                            else:
                                err = f"Error while reading ssm parameter {cid_error_status}"
                                input = {"error" : str(err), "resource_id" : instance_id, "resource_type" : "EC2 Instance"}
                                return failure_token(task_token, input, cid_error_status)
                    else:
                        print("Cli  is not Present")   
                        print(event)
                else:
                    print("SSM or public_ip is not present for this server")
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
