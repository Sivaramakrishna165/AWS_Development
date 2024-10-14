"""
    The main purpose of this script is to read the name 
    of health check script from YAML file and than take 
    that script from S3 Bucket and run it on the all the suitable 
    EC2 instances and save the standard output in the Cloud Watch.

    Input Example: {"S3_Bucket":"bucket-for-testing-221", "S3_directory_name":"feature_aws_health_checks/", "uniqueID": "healthCheckJobId_xxxxxxxxxxxx"}
"""

import json
import csv
import boto3
import yaml
import sys
import os
from datetime import datetime
from botocore.config import Config



config=Config(retries=dict(max_attempts=10,mode='standard'))

SSM_CWLogGroupName= os.environ['SSM_CWLogGroupName']
sns_ARN = os.environ['sns_ARN']
send_cmd_IAM = os.environ['send_cmd_IAM']

# SSM_CWLogGroupName = "/aws/ssm/AWS-RunPowerShellScript"
# sns_ARN = "arn:aws:sns:ap-south-1:338395754338:Notify_Team"
# send_cmd_IAM = "arn:aws:iam::338395754338:role/dxc_pa_iam_sns_role"

uniqueID = ""
table_name = os.environ['table_name']
# not_to_be_included = ['Unknown']

s3 = boto3.resource('s3', config=config)


'''
    This function will return the Line 
    number and the error that occured.
'''
def PrintException():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    captureErr = "Line No. : " + str(lineno)  + " | ERROR: " + str(exc_obj)
    return captureErr


'''
    This function is reading the CSV file from the 
    S3 bucket and then create seperate list of 
    each OS and the calling run command function. 
'''
def server_list_reader(bucket_name, dir_uri, server_list_bucket_uri):
    
    rows = []
    # status = False
    # info_dict = {}
    json_config_data = {}
    os_flavour = set()
    os_column_name = "Technology"
    count = 0
    try:
        s3_object = s3.Object(bucket_name, server_list_bucket_uri)
    except:
        exception = PrintException()
        print(exception)
        issue_put_data("S3 Bucket", "Get server_report object", "Failed to read object", exception)
        print("================================")
        print("Error Occured while downloading Server List File.")
        print("Bucket Name: "+bucket_name)
        print("Key Used: "+server_list_bucket_uri)
        print("================================")
    else:
        try:
            # Read data from the file
            data = s3_object.get()['Body'].read().decode('utf-8').splitlines()
            csvreader = csv.reader(data)

            header = next(csvreader)
            #print(header)
            
            platform_index= header.index(os_column_name)
            
            for row in csvreader:
                if not (str(row[platform_index]) == "Unknown"):
                    os_flavour.add(str(row[platform_index]))
                    rows.append(row)
                
            print(os_flavour)
            print(len(rows))
        except:
            exception = PrintException()
            print(exception)
            issue_put_data("Server_Report", "Read server_report", "Failed to read server_report", exception)
            
        else:
            
            if os_flavour and rows:
                    
                for os in os_flavour:
                    #print(region)
                    instance_list = []
                    s3_uri = dir_uri+'aws_health_check_low_level_scripts/'+os+'/'
                    for roww in rows:
                        if str(roww[platform_index]) == os:
                            instance_list.append(roww[2])
                    
                    print("OS Flavour: ", os)
                    
                    health_check_names = yaml_file_reader(bucket_name, s3_uri+'health_check_config_'+os+'.yml', os)
                    #print(region)
                    
                    for health_check_name in health_check_names:
                        print("Health Check: ", health_check_name)
                        
                        hc_get_data(f"{os}-{health_check_name}")

                        instance_id_list = validate_instance(instance_list, f"{os}-{health_check_name}")
                           
                        # counter = counter+ len(instance_id_list)
                        if instance_id_list:

                            count = count+ len(instance_id_list)
                            command_id = run_command(bucket_name, s3_uri, health_check_name, os)    
                            if command_id:
                                json_config_data = generate_json_data(json_config_data, os, health_check_name, command_id)

                        else:
                            
                            print(f"Health Check: {os}-{health_check_name} No Valid Instance available")
                            issue_put_data(f"Health Check: {os}-{health_check_name}", "Validating Instances", "No Valid Instance Available", "")
                            continue
                
                # print(commandID_list)
                return json_config_data, count
            else:
                print("================================")
                print("No Valid Instances Found")
                print("OS supported Flavour: "+str(os_flavour))
                issue_put_data("EC2 Instance", "Listing supported OS Flavour", "No Supported Instances Found", "")
                print("================================")


'''
    This function is reading the YAML configuration 
    file from S3 bucket and creating list of all 
    health checks int it.
'''
def yaml_file_reader(bucket_name, yaml_file_uri, os):

    s3_client = boto3.client('s3', config=config)
    # global column_name, condition, threshold
    healthcheck_list = []
    exclusion_dict = {}

    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=yaml_file_uri)
        data = yaml.safe_load(response["Body"])
        #print(data)
    except:
        exception = PrintException()
        print(exception)
        issue_put_data("S3 Bucket", "Locating Config File: "+yaml_file_uri, f"{os} specific health check script or config file unavailable", exception)
        print("================================")
        print("Error Occured while Loading YAML File.")
        print("Bucket Name: "+bucket_name)
        print("Key Used: "+yaml_file_uri)
        print("================================")
    
    else:
        try:
            #print(data['DORM_Health_Checks'][0]['Sub_Checks'][0])
            for dorm_Health_check in data['DORM_Health_Checks']:
                if (dorm_Health_check['DORM_Check_Name'] == None or dorm_Health_check['Check_Id'] == None):
                    issue_put_data(f"{os} Config YAML", "Reading YAML Health Checks", "DORM_Check_Name/Check_Id not available", "")
                    continue
                for sub_checks in dorm_Health_check['Sub_Checks']:
                    sub_Check_Name = sub_checks['Name']
                    # exclusion_instances = sub_checks['Exclusion_List']
                    # exclusion_instances = [] if exclusion_instances == None else exclusion_instances.replace(" ", "").split(",")

                    #print(sub_Check_Name)
                    healthcheck_list.append(sub_Check_Name)
                    # exclusion_dict[sub_Check_Name] = exclusion_instances
        except:
            exception = PrintException()
            print(exception)
            issue_put_data(f"{os} Config YAML", "Reading YAML Health Checks", "Error Occured while reading Config file", "")
            print("================================")
            print("Error Occured while Reading YAML File.")
            print("================================")
        
    return healthcheck_list #, exclusion_dict


def validate_instance(instance_list, hc_name):

    print("validate_instance called")
    working_instances_list = []

    try:
        working_instances_list = instance_state(instance_list, hc_name)
        if working_instances_list:
            working_instances_list = get_ssm_status(working_instances_list, hc_name)

            # if working_instances_list and exclusion_list:
            #     working_instances_list = remove_exclusion_instances(working_instances_list, exclusion_list, hc_name)

        return working_instances_list
    except:
        print(PrintException())


'''
    This function is checking the state of 
    each instance provided in the list and 
    returning only list of those instance that 
    are running.
'''
def instance_state(instance_list, hc_name):
    
    print("instance_state called")
    instance_running = []
    # invalid_state_instances = []
    ec2 = boto3.resource('ec2', config=config)
    
    for instance_id in instance_list:
        try:   
            instance = ec2.Instance(instance_id)
            instance_state = instance.state['Name']
            print("Instance ID: ",instance_id, "  ||  Instance State: ",instance_state)
            if instance_state == 'running':
                instance_running.append(instance_id)
            else:
                # invalid_state_instances.append(instance_id)
                hc_put_data(hc_name, f"EC2 Instance:{instance_id}", "Validating Instance", f"Invalid Instance State:{instance_state}")
        # if invalid_state_instances:
        except:
            exception = PrintException()
            print(exception) 
            issue_put_data(f"EC2 Instance: {instance_id}", "Instance State Validation", "Failed to Validate Instance State", exception)
    return instance_running



def get_ssm_status(instance_list, hc_name):

    print("get_ssm_status called")
    ssm_enabled_instance_list = []
    #invalid_state_instances = []
    
    try:
        ssm_client = boto3.client('ssm',config=config)
        response = ssm_client.describe_instance_information(
            InstanceInformationFilterList=[
                { 'key': 'InstanceIds', 'valueSet': instance_list },
            ],
        )

    # Checks if 'InstanceInformationList' list is empty or not.
        if not (len(response['InstanceInformationList']) == 0):
            for item in response['InstanceInformationList']:
                print("Instance ID: ",item['InstanceId'], "  ||  SSM Status: ",item['PingStatus'])
                if item['PingStatus'] == "Online":
                    ssm_enabled_instance_list.append(item['InstanceId'])
                # else:
                #     invalid_state_instances.append(item['InstanceId'])

        # invalid_state_instances = [instance_id_list for instance_id_list in instance_list if instance_id_list not in ssm_enabled_instance_list]

        for instance_id in instance_list:
            if instance_id not in ssm_enabled_instance_list:
                print("Instance ID: ",instance_id, "  ||  SSM Status:  Offline")
                hc_put_data(hc_name, f"EC2 Instance:{instance_id}", "Validating Instance", "Invalid SSM State: Offline")
        
        return ssm_enabled_instance_list
        
    except:
        print(PrintException())


'''
    This function is running low level health 
    check script on EC2 instance list provided to it.
'''
def run_command(bucket_name, s3_uri, health_check_name, platform):
    
    cmd_id = ""
    bucket = s3.Bucket(bucket_name)
    client = boto3.client("ssm", config=config)

    col_name = (f"{platform}-{health_check_name}").replace(" ", "_")
    payload_dict = json.dumps({"uniqueID": uniqueID, "health_check": col_name})

    try:
        script_name = 'AWS-RunPowerShellScript' if 'windows' in str(platform).lower() else 'AWS-RunShellScript'
        object = bucket.Object(s3_uri+health_check_name+'.sh') if script_name == 'AWS-RunShellScript' else bucket.Object(s3_uri+health_check_name+'.ps1')
        filedata = object.get()['Body'].read().decode("utf-8")
        #print(filedata)
    except:
        exception = PrintException()
        print(exception)
        hc_put_data(col_name,"S3 Bucket", f"Unable to read script: {s3_uri+health_check_name}", exception)
        print("================================")
        print("Error Occured while Reading Script.")
        print("Script Name: "+ health_check_name)
        print("Key: "+ s3_uri)
        print("================================")

    else:
            
        try:
            
            response = client.send_command(
                    # InstanceIds= instance_id_list,
                    Targets=[
                        {
                            'Key': f"tag:DXC_healthCheck",
                            'Values': [ f"hc-{platform.replace(' ', '_')}" ]
                        },
                    ],
                    DocumentName = script_name,
                    DocumentVersion= '1',
                    TimeoutSeconds= 120,
                    Parameters={
                        'commands': [
                            filedata,
                            ]
                        },
                    MaxConcurrency='50%',
                    MaxErrors='100%',
                    OutputS3BucketName= bucket_name,
                    OutputS3KeyPrefix= "temp_data/"+str(payload_dict),
                    ServiceRoleArn = send_cmd_IAM,
                    NotificationConfig={
                        'NotificationArn': sns_ARN,
                        'NotificationEvents': [
                            'TimedOut','Cancelled','Failed',
                        ],
                        'NotificationType': 'Invocation'
                    },
                    
                    CloudWatchOutputConfig={
                    'CloudWatchLogGroupName': SSM_CWLogGroupName,
                    'CloudWatchOutputEnabled': True
                    }
                )

            cmd_id = response['Command']['CommandId']
        except:
            exception = PrintException()
            print(exception)
            hc_put_data(col_name, "SSM Send Command", f"Unable to send command", exception)
            print("================================")
            print("One or More Instances are not in a Valid State")
            print("================================")

        # tag_remover(instance_id_list, f"{platform}_{health_check_name}")

    return cmd_id


'''
    This function is generating the json object 
'''
def generate_json_data(json_config_data, platform, health_check_name, command_ID):
    try:

        if platform not in json_config_data:
            json_config_data[platform] = []

        json_config_data[platform].append({
                            health_check_name: command_ID
                        })
        
        return json_config_data
    except:
        exception = PrintException()
        print(exception)
        issue_put_data("ResourceName", "JSON Config Creation", "Error Occurred", exception)


'''
    This function takes file uri and JSON Object that needs 
    to be added and then creates the JSON file for it.
'''
def create_json_file(local_file_uri, json_object): 
    print("create_json_file called")
    try:
        with open(local_file_uri, "w", newline='') as outfile:
            outfile.write(str(json_object))
    except:
        print(PrintException())
        print("================================")
        print("Error While creatinging JSON File")
        print("Local File Uri: "+ str(local_file_uri))
        print("JSON Data: "+ str(json_object))
        print("================================")


'''
    This function upload the given file uri to 
    the S3 bucket and at particular key loacation provided.
'''
def upload_file(file_uri, bucket_name, key):
    print("upload_file called")
    try:
        s3.meta.client.upload_file(file_uri, bucket_name, key)
        print("File Saved at: "+ key)
        return True
    except:
        print(PrintException())
        print("================================")
        print("Error While uploading File")
        print("Bucket Name: "+ str(bucket_name))
        print("Key: "+ str(key))
        print("================================")
        return False


def issue_put_data(ResourceName, TaskName, Result, Exception):
    
    print("issue_put_data called")
    # global hc_issue_count
    #issue_count = issue_count + 1
    now = datetime.now()
    key_name = os.environ['AWS_LAMBDA_FUNCTION_NAME']
    dynamodb_resource = boto3.resource('dynamodb',config=config)
    table = dynamodb_resource.Table(table_name)
    
    try:  
        table.update_item(
        Key={
            'AWS_HealthCheck_UUI': uniqueID},
        UpdateExpression= f'SET {key_name} = list_append({key_name}, :obj)',
        ExpressionAttributeValues={
            ":obj": [
                    {
                        'ResourceName': ResourceName,
                        'TaskName': TaskName,
                        'Result': Result,
                        'Exception': Exception,
                        'Timestamp': now.strftime("%d/%m/%Y %H:%M:%S")
                    }
                ]}
        )
    except:
        print(PrintException())
        print("Error during table.update_item")


def hc_get_data(key_name):
    print("hc_get_data called")
    key_name = key_name.replace(" ", "_")
    dynamodb = boto3.resource('dynamodb',config=config)
    table = dynamodb.Table(table_name)
    response = table.get_item(TableName=table_name, Key={'AWS_HealthCheck_UUI':uniqueID})
    if key_name not in response['Item']['health_checks']:
        print(f"Unable to find {key_name} key")
        hc_put_key(key_name, True)


def hc_put_key(hc_name, flag):

    print("hc_put_key called")
    dynamodb_resource = boto3.resource('dynamodb',config=config)
    table = dynamodb_resource.Table(table_name)
    print(f"Creating {hc_name}")
    try:
        if flag:
            response = table.update_item(
                Key={
                    'AWS_HealthCheck_UUI': uniqueID},
                    UpdateExpression=f'SET health_checks.#hc_name = :obj',
                    ExpressionAttributeNames = { "#hc_name" : hc_name},
                    ExpressionAttributeValues={":obj": []}
                )
        else:
            response = table.update_item(
                Key={
                    'AWS_HealthCheck_UUI': uniqueID},
                    UpdateExpression=f'SET #hc_name = :obj',
                    ExpressionAttributeNames = { "#hc_name" : hc_name},
                    ExpressionAttributeValues={":obj": []}
                )

        
    except:
        print(PrintException())
        print("Error during table.put_item")


'''
    This function is 
'''
def hc_put_data(hc_name, ResourceName, TaskName, Result):
    
    print("hc_put_data called")
    # global hc_issue_count
    #hc_issue_count = hc_issue_count + 1
    now = datetime.now()
    hc_name = hc_name.replace(" ", "_")

    dynamodb_resource = boto3.resource('dynamodb',config=config)
    table = dynamodb_resource.Table(table_name)
    
    try:  
        table.update_item(
        Key={
            'AWS_HealthCheck_UUI': uniqueID},
        UpdateExpression= 'SET health_checks.#hc_name = list_append(health_checks.#hc_name, :obj)',
        ExpressionAttributeNames = { "#hc_name" : hc_name},
        ExpressionAttributeValues={
            ":obj": [
                    {
                        'ResourceName': ResourceName,
                        'TaskName': TaskName,
                        'Result': Result,
                        'Timestamp': now.strftime("%d/%m/%Y %H:%M:%S")
                    }
                ]}
        )
    except:
        print(PrintException())
        print("Error during table.update_item")


'''
    This function is used to validate 
    the token sent by stepfunction
'''
def token(event, task_token):

    sf = boto3.client('stepfunctions')
    sf_output = json.dumps(event)
    # task_token = event['token']

    sf_response = sf.send_task_success(
        taskToken=task_token,
        output=str(sf_output)
    )

    return sf_response



def lambda_handler(event, context):
    # TODO implement

    print("Event Recieved: ", event)
    task_token = event['token']
    event = event["Payload"]

    global uniqueID
    uniqueID = event["uniqueID"]
    bucket_name = event["S3_Bucket"]

    hc_put_key(os.environ['AWS_LAMBDA_FUNCTION_NAME'], False)
    json_file_name = 'health_check_config_file.json'
    json_bucket_uri = event["S3_directory_name"]+ 'inventory/'+json_file_name
    local_file_uri = "/tmp/"+json_file_name
    dir_uri = event["S3_directory_name"]+ "aws_server_health_check/"

    json_config_data, instanceCount = server_list_reader(bucket_name, dir_uri, f"{event['S3_directory_name']}inventory/server_list_report.csv")

    totalExecutionMinutes = int(instanceCount) * 5
    totalExecutionMinutes = totalExecutionMinutes * 2
    count = (totalExecutionMinutes / 10)
    
    if json_config_data:
        print("JSON Data: ", json_config_data)
        create_json_file(local_file_uri, json.dumps(json_config_data))
        try:
            
            if upload_file(local_file_uri, bucket_name, json_bucket_uri):
                event['Status'] = 'pending'
                event['Count'] = count
                return token(event, task_token)
        except:
            print(PrintException())
    else:
        event['Status'] = 'completed'
        event['Count'] = 0
        return token(event, task_token)


    # create_json_file(local_file_uri, json_config_data)
    # upload_file(local_file_uri, bucket_name, json_bucket_uri)

    # return token(event, task_token)


if __name__ == "__main__":
    event1= {"S3_Bucket":"bucket-for-testing-221", "S3_directory_name":"feature_aws_health_checks/", "uniqueID": "healthCheckJobId_xxxxxxxxxxxx"}
    lambda_handler(event1, "")