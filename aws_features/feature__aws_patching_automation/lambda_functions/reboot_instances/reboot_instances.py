
'''
This Lambda function reboots the successfully patched independent instances.
It also reboots the source instances  defined in the configuration in SSM Parameter.
It returns the list of servers for which status needs to be checked after reboot.
'''

import boto3
import json
import sys
import os
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))
ssm_client_document = boto3.client('ssm',config=config)
wait_time_parameter = os.environ['WaitTimeRetry']

def PrintException():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    captureErr = "Line No. : " + str(lineno)  + " | ERROR: " + str(exc_obj)
    return captureErr

#read ssm parameter for reboot sequence
def read_ssm_parameter(ssm_parameter):
    try:
        ssm_client = boto3.client('ssm',config=config)
        try:
            ssmParameter = ssm_client.get_parameter(Name=ssm_parameter)
            reboot_server_sequence = json.loads(ssmParameter['Parameter']['Value'])
            source_server_list = []
            dependent_server_list = []
            for source_server,dependent_server in reboot_server_sequence.items():
                source_server_list.append(source_server)
                dependent_server_list.append(dependent_server)
            return source_server_list,dependent_server_list,reboot_server_sequence
        except:
            print(PrintException())
            print("Error while reading SSM Parameter - ",ssm_parameter,". Hence, It will consider that there is no source and dependent servers.")
            return [],[]
    except:
        print(PrintException())

#Check instance platform
def check_instance_type(instance_id):
    try:
        ec2_client = boto3.client("ec2",region_name = region,config=config)
        response = ec2_client.describe_instances(InstanceIds=[instance_id,])
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                try:
                    platform = instance['Platform']
                except:
                    platform = 'linux'
        return platform
    except:
        print(PrintException())

#Check Instance reachability before reboot
def check_instance_status(instance_id):
    client = boto3.client('ec2',region_name = region,config=config)
    try:
        response = client.describe_instance_status(InstanceIds=[instance_id,])
        Instance_status = response['InstanceStatuses'][0]['InstanceState']['Name']
        print("Instance Id : ", instance_id , "Status of Instance : ", Instance_status)
        if Instance_status:
            SERVER_REACHABILITY = 'Yes'
        return SERVER_REACHABILITY
    except:
        error = PrintException()
        #print(error)
        if error:
            SERVER_REACHABILITY = 'No'
        return SERVER_REACHABILITY

# fetch the document hash value
def get_document_hash(document_name):
    try:
        response = ssm_client_document.describe_document(
            Name=document_name
        )
        hash_value = response['Document']['Hash']
    except Exception as e:
        hash_value = ''
    return hash_value

#Check reachability after reboot
def check_window_server_reachability(instance_id,bucket_name,S3_directory_name):
    ssm_client = boto3.client('ssm',region_name = region,config=config)
    S3_prefix = S3_folder +"/PATCHING/"+S3_directory_name+"/reboot_logs"
    #print("Reboot Logs path:",bucket_name, S3_prefix)
    try:
        document_hash = get_document_hash('AWS-RunPowerShellScript')
        response = ssm_client.send_command(
            InstanceIds=[
                instance_id,
            ],
            DocumentName='AWS-RunPowerShellScript',
            DocumentHash=document_hash,
            DocumentHashType='Sha256',
            TimeoutSeconds=600,
            Parameters={
                'commands': ["hostname",]
            },
            OutputS3BucketName=bucket_name,
            OutputS3KeyPrefix=S3_prefix)
        command_id = response['Command']['CommandId']
        print("Command_Id : ",command_id)
        cmd_status = response['Command']['Status']
        print("Command_Status : ",cmd_status)
        return command_id,cmd_status
    except:
        error = PrintException()
        print("Error : ",error)
        
   

#Check reachability after reboot
def check_linux_server_reachability(instance_id,bucket_name,S3_directory_name):
    ssm_client = boto3.client('ssm',region_name = region,config=config)
    S3_prefix = S3_folder +"/PATCHING/"+S3_directory_name+"/reboot_logs"
    #print("Reboot Logs path:",bucket_name, S3_prefix)
    try:
        document_hash = get_document_hash('AWS-RunShellScript')
        response = ssm_client.send_command(
            InstanceIds=[
                instance_id,
            ],
            DocumentName='AWS-RunShellScript',
            DocumentHash=document_hash,
            DocumentHashType='Sha256',
            TimeoutSeconds=600,
            Parameters={
                'commands': ["hostname",]
            },
            OutputS3BucketName=bucket_name,
            OutputS3KeyPrefix=S3_prefix )
        command_id = response['Command']['CommandId']
        print("Command_Id : ",command_id)
        cmd_status = response['Command']['Status']
        print("Command_Status : ",cmd_status)
        return command_id,cmd_status
    except:
        error = PrintException()
        print("Error : ",error)



#Get instances for which 'Reboot' tag is specified as 'Yes'
def get_reboot_options(successfullInstanceIds):
    try:
        ec2_client = boto3.client('ec2',region_name = region,config=config)
        reboot_filter = [{ 'Name':'tag:Reboot', 
                        'Values': ['Yes']}]
        ec2_list = ec2_client.describe_instances(Filters=reboot_filter,InstanceIds=successfullInstanceIds)
        rebootinstanceids = [instance['InstanceId'] for ec2 in ec2_list['Reservations']  for instance in ec2["Instances"]]
    except:
        error = PrintException()
        print("Error : ",error)
    return rebootinstanceids
    
#Reboots only source instances
def reboot_source_instances(instance_ids,bucket_name,S3_directory_name,patchJob_id):
    try:
        ec2_client = boto3.client('ec2',region_name = region,config=config)
        reboot_server_sequence = read_item_dynamoDB(patchJob_id,"updated_reboot_sequence") #Read updated successful source and dependents
        source_servers = []
        dependent_server = []
        new_sequence = {}
        for source,dependent in reboot_server_sequence.items():
            if source in instance_ids:
                source_servers.append(source)
                dependent_server.append(dependent)
                new_sequence[source] = dependent
        print("Source Servers which have Patch InstallOn Tag : ", source_servers)
        print("Dependent Servers are : ", dependent_server)
        #source_servers = list(set(instance_ids).intersection(source_server)) #successfully patched source instances
        
        for i in range(len(source_servers)): 
            instance_platform = check_instance_type(source_servers[i])
            print("Source Server : ",source_servers[i], i)
            print("instance_platform ",instance_platform)
            server_reachability = check_instance_status(source_servers[i])
            if server_reachability == 'Yes':
                response = ec2_client.reboot_instances(InstanceIds=[source_servers[i],])
                print("source server rebooted : ",response)
                if len(dependent_server[i]) > 0:
                    if instance_platform == 'linux': #If Platform is Linux
                        server_status_after_reboot = check_linux_server_reachability(source_servers[i],bucket_name,S3_directory_name)
                    else : #If Platform is Windows
                        server_status_after_reboot = check_window_server_reachability(source_servers[i],bucket_name,S3_directory_name)
                    print("Source Server:",source_servers[i],"Status after reboot:", server_status_after_reboot)
        return new_sequence
    except:
        print(PrintException())

#Reboot all instances other than source and dependent instances               
def reboot_all_instances(ec2_instance_ids):
    try:
        ec2_client = boto3.client('ec2',region_name = region,config=config)    
        response = ec2_client.reboot_instances( InstanceIds=ec2_instance_ids)
        print("Reboot Response : ",response)
    except:
        print(PrintException())

#Get successfully patched instances details
def read_item_dynamoDB(patchJob_id,keyname):
    dynamodb = boto3.resource('dynamodb')
    patch_table = dynamodb.Table('Ft_dxcms_patching_e2e_automation')

    try:
        response = patch_table.get_item(Key={'patchJob_id': patchJob_id})
        itemsFromTable = response['Item']
        
        patchInstallStatusOfInstances = itemsFromTable[keyname]
        return patchInstallStatusOfInstances
    except:
        print(PrintException())

#Update Reboot Sequence to Reboot only successful dependents
def call_update_dynamodb_lambda_fun(patchJob_id,attribute_name,attribute_value):
    try:
        lambda_client = boto3.client('lambda',config=config)
        dynamo_event = {'patchJob_id': patchJob_id,'attribute_name':attribute_name,'attribute_value':attribute_value}
        response = lambda_client.invoke(
            FunctionName='dxcms-pa-lam-update-dynamodb',
            Payload=json.dumps(dynamo_event)
        )
    except:
        print(PrintException())


def get_aws_account_info():
    accoundId = ""
    try:
        sts = boto3.client("sts",config=config)
        accoundId = sts.get_caller_identity()["Account"]    
    except:
        print(PrintException())
        accoundId = ""
    return accoundId

#read ssm parameter for reboot wait time
def read_ssm_parameter_wait_time(wait_time_parameter):
    try:
        ssm_client = boto3.client('ssm',config=config)
        try:
            ssmParameter = ssm_client.get_parameter(Name=wait_time_parameter)
            ssm_param_value = json.loads(ssmParameter['Parameter']['Value'])
            wait_time_mins = ssm_param_value["Wait"]
            wait_time = wait_time_mins*60
            return wait_time
        except:
            print(PrintException())
            print("Error while reading SSM Parameter - ",wait_time_parameter,". Taking Default value of 5 mins")
            return 300
    except:
        print(PrintException())

def lambda_handler(event, context):
    try:
        global bucket_name, S3_directory_name, local_Folder, S3_folder, region, patchJobId
        global ssm_parameter
        successfullInstanceIds = []
        allSourceDependentInstances = []
        
        tagValue = event['PatchInstallOn']
        bucket_name = event['S3_Bucket']
        S3_directory_name = event['S3_directory_name']
        S3_folder = event['S3_Folder_Name']   
        
        region = event['region']
        patchJobId = S3_directory_name.split("/")[2]

        account_id = get_aws_account_info()
        Patching_Type = event['Patching_Type']
        if Patching_Type == 'Standard':
            patching_tag = "PatchInstallOn"
            InstanceRebootSequence = os.environ['InstanceRebootSequence'] # "/DXC/PatchingAutomation/Instance_Reboot_Sequence_"
            ssm_parameter = InstanceRebootSequence + region
        else:
            patching_tag = "AdhocPatchInstallOn"
            AdhocInstanceRebootSequence = os.environ['AdhocInstanceRebootSequence'] # '/DXC/AdhocPatchingAutomation/Instance_Reboot_Sequence_'
            ssm_parameter = AdhocInstanceRebootSequence + region
        
        patchInstallStatusOfInstances = read_item_dynamoDB(patchJobId,"patch_installed_instances") 
        print("patchInstallStatusOfInstances : ", patchInstallStatusOfInstances) 

        for instanceId,patchStatus in patchInstallStatusOfInstances.items():
            if patchStatus == "Success":
                successfullInstanceIds.append(instanceId)
        
        print("Successful Instance IDs are : ", successfullInstanceIds)
        #Get reboot options from 'Reboot' tag for successfully patched instances
        successfullInstanceIds = get_reboot_options(successfullInstanceIds)
        print("Successful Instance IDs which are allowed reboot : ", successfullInstanceIds)
        
        source_server, dependent_server ,reboot_server_sequence = read_ssm_parameter(ssm_parameter)
        sourceAndDependentServers = source_server + dependent_server
        
        for i in sourceAndDependentServers:
            if type(i) == list:
                for x in i:
                    allSourceDependentInstances.append(x)
            else:
                allSourceDependentInstances.append(i)
              
        #All successfully patched source and dependent instances
        commonMatchedInstances = list(set(successfullInstanceIds).intersection(allSourceDependentInstances))
        #All successfully patched other instances which are not source or dependent
        rebootAllInstances = list(set(successfullInstanceIds).difference(commonMatchedInstances))
        if len(rebootAllInstances) == 0:
            rebootAllInstances = list(set(commonMatchedInstances).difference(successfullInstanceIds))
        
        print("Reboot all Instances at a time : ", rebootAllInstances)
        reboot_all_instances(rebootAllInstances)
        
        #Update Reboot Sequence to Reboot only successful dependents
        updated_reboot_sequence = {}
        print("Original Reboot Sequence:",reboot_server_sequence)
        for source,dependent in reboot_server_sequence.items():
            updated_dependents = [d for d in dependent if d in successfullInstanceIds]
            print("Updated Dependents:",updated_dependents)
            updated_reboot_sequence.update({source: updated_dependents})
        call_update_dynamodb_lambda_fun(patchJobId,"updated_reboot_sequence",updated_reboot_sequence)
        print("Updated Reboot Sequence :", updated_reboot_sequence)
        
        #Reboot successfully patched source instances
        new_reboot_server_sequence = reboot_source_instances(successfullInstanceIds,bucket_name,S3_directory_name,patchJobId)       
        event['Updated_reboot_sequence'] = new_reboot_server_sequence
        event['Wait_time'] = read_ssm_parameter_wait_time(wait_time_parameter)
        
        return event
    except:
        print(PrintException())
# simple test cases

if __name__ == "__main__":
    event1 = {
  "PatchInstallOn": "DEV-NOV_1_2021_13_30_4HRS_BY_AY",
  "S3_Bucket": "dxc",
  "S3_directory_name": "OCT_2021/ap-south-1/patchJobId_968e4f46-145e-11ec-963a-91da71649e83",
  "CommandId": "79abcb2d-7af1-46eb-95ff-fd47ba77b7ab",
  "Status": "pending",
  "app_action": "start",
  "region":"ap-south-1",
  "S3_Folder_Name": "Patching_Automation_Reports"
}
    lambda_handler(event1, "") 
