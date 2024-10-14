'''
This Lambda script enables/disables the alarms which are associated to the instance.
'''

import boto3
from botocore.client import Config
import json
import time, sys, datetime
from datetime import datetime
import csv, os
import re
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))
       
def PrintException():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    captureErr = "Line No. : " + str(lineno)  + " | ERROR: " + str(exc_obj)
    return captureErr

def IsObjectExists(path):
    try:
        s3 = boto3.resource('s3')
        bucket = s3.Bucket(bucket_name)
        for object_summary in bucket.objects.filter(Prefix=path):
            return True
        return False
    except:
        print(PrintException())
    
def upload_file_into_s3(fileFullName_Local,fileFullName_S3):
    try:
        s3_resource = boto3.resource('s3', config=Config(signature_version='s3v4'))
        bucket = s3_resource.Bucket(bucket_name)
        Key = fileFullName_S3
        print("Key : ", Key)
        print("fileFullName_Local : ",fileFullName_Local)
        bucket.upload_file(fileFullName_Local, Key)
    except:
        print(PrintException())
    
def download_file_from_S3_bucket(fileFullName_Local,fileFullName_S3):
    s3client = boto3.client('s3',config=config)
    try:
        #fileFullName_Local = "c:\\temp\\report.csv"
        #Key = 'PATCHING/' + S3_directory_name + '/' + errorLogFileName
        Key = fileFullName_S3        
        s3client.download_file(bucket_name, Key, fileFullName_Local)
        return True
    except:
        print(PrintException())
        return False
 
def write_csv_file(stepName,resource,errorMsg):
    try:
        with open(errorLog_Local_FullFileName, 'a', newline='') as csvfile:
            filewriter = csv.writer(csvfile, delimiter=',')        
            filewriter.writerow([stepName,resource,errorMsg])
    except:
        print(PrintException())
        
def write_csv_file_report(resource,AlarmName,AlarmType,status,Alarm_state):
    try:
        with open(alarmReport_Local_FullFileName, 'a', newline='') as csvfile:
            filewriter = csv.writer(csvfile, delimiter=',')        
            filewriter.writerow([resource,AlarmName,AlarmType,status,Alarm_state])
    except:
        print(PrintException())


def call_update_dynamodb_lambda_function(patchJob_id,attribute_name,attribute_value):
    lambda_client = boto3.client('lambda',config=config)
    dynamo_event = {'patchJob_id': patchJob_id,'attribute_name':attribute_name,'attribute_value':attribute_value}
    response = lambda_client.invoke(
        FunctionName='dxcms-pa-lam-update-dynamodb',
        Payload=json.dumps(dynamo_event)
    )


def alarm_action(Action,InstanceList,instanceIPs,next_token):
    try:
        alarm_client = boto3.client('cloudwatch',config=config)
        MaxRecords = 40
        if next_token == "" or next_token == None:        
            alarms = alarm_client.describe_alarms(MaxRecords=MaxRecords)
            try:
                next_token = alarms['NextToken']
            except:
                next_token = None
        else:
            alarms = alarm_client.describe_alarms(MaxRecords=MaxRecords,NextToken=next_token)
            try:
                next_token = alarms['NextToken']
            except:
                next_token = None
            
        for alarm in alarms['MetricAlarms']:
            #Alarm for EC2 Instances
            #print("ALARM NAMESPACE : ============> ", alarm['Namespace'])
            if alarm['Namespace'] == 'AWS/EC2':
                for d in alarm['Dimensions']:
                    if d['Name'] == 'InstanceId' and d['Value'] in InstanceList:
                        print("\nType : EC2")
                        print("EC2 Instance ID : ", d['Value'])
                        print("EC2 Alarm Name : ", alarm['AlarmName'])
                        if Action == "enable":
                            print(
                                f"Enabling alarm_actions for: { alarm['AlarmName']}")
                            try:
                                alarm_client.enable_alarm_actions(AlarmNames=[alarm['AlarmName']])
                                alarm_client.set_alarm_state(AlarmName=alarm['AlarmName'],StateValue='OK',StateReason='automation script after enabling alarm')
                                stepName = Action + " Alarm"
                                alarm_state = get_alarm_state(alarm['AlarmName'])
                                write_csv_file_report(d['Value'],alarm['AlarmName'],'EC2','Success',alarm_state)
                            except:
                                err = PrintException()
                                print(err)
                                stepName = Action + " Alarm"
                                write_csv_file(stepName,alarm['AlarmName'],err)
                                alarm_state = get_alarm_state(alarm['AlarmName'])
                                write_csv_file_report(d['Value'],alarm['AlarmName'],'EC2',err,alarm_state)
                                call_update_dynamodb_lambda_function(patchJob_id,attribute_name='app_status',attribute_value='started')
                                time.sleep(10)
                                call_update_dynamodb_lambda_function(patchJob_id,attribute_name='patch_job_status',attribute_value='completed')
                        if Action == "disable":
                            print(
                                f"Disabling alarm_actions for: { alarm['AlarmName']}")
                            try:
                                alarm_client.disable_alarm_actions(AlarmNames=[alarm['AlarmName']])
                                alarm_state = get_alarm_state(alarm['AlarmName'])
                                write_csv_file_report(d['Value'],alarm['AlarmName'],'EC2','Success',alarm_state)
                            except:
                                err = PrintException()
                                print(err)
                                stepName = Action + " Alarm"
                                write_csv_file(stepName,alarm['AlarmName'],err)
                                alarm_state = get_alarm_state(alarm['AlarmName'])
                                write_csv_file_report(d['Value'],alarm['AlarmName'],'EC2',err,alarm_state)
                            
            
            #Alarm for Classic Load Balancer            
            if alarm['Namespace'] == 'AWS/ELB':
                for elb_d in alarm['Dimensions']:
                    classic_elb_alarm(Action,alarm['AlarmName'],elb_d['Value'],InstanceList) 
                    
            #Alarm for Application Load Balancer
            if alarm['Namespace'] == 'AWS/ApplicationELB' or alarm['Namespace'] == 'AWS/NetworkELB':
                targetGroups = []
                for alb_d in alarm['Dimensions']:
                    if alb_d['Name'] == "TargetGroup":
                        if "/" in alb_d['Name']:
                            targetGroup = alb_d['Value'].split("/")[1]
                        else:
                            targetGroup = alb_d['Value']
                        targetGroups.append(targetGroup)
                application_elb_alarm(Action,alarm['AlarmName'],targetGroups,InstanceList,instanceIPs,alarm['Namespace'].split("/")[1])
        
        if next_token != None:
            alarm_action(Action,InstanceList,instanceIPs,next_token)  
    except:
        err = PrintException()
        print(err) 


def classic_elb_alarm(Action,AlarmName,ELBName,InstanceList): 
    try:
        elb_client = boto3.client('elb',config=config)
        alarm_client = boto3.client('cloudwatch',config=config)
        elbInstancelist = []
        loadBalancers = elb_client.describe_load_balancers(LoadBalancerNames=[ELBName])
        print("loadBalancers : ",loadBalancers)
        for elb in loadBalancers['LoadBalancerDescriptions']:
            for elbInstance in elb['Instances']:
                elbInstancelist.append(elbInstance['InstanceId'])
        # It will disable/enable ELB alarm even if one instance is part of ELB
        if any(item in InstanceList for item in elbInstancelist):
            print("\nType : ELB CLASSIC")
            print("ELB Name : ", ELBName)
            print("ELB Alarm Name : ", AlarmName)
            if Action == "enable":
                print(
                    f"Enabling alarm_actions for ELB : { AlarmName }")
                try:
                    alarm_client.enable_alarm_actions(AlarmNames=[AlarmName])
                    alarm_client.set_alarm_state(AlarmName=AlarmName,StateValue='OK',StateReason='automation script after enabling alarm')
                    alarm_state = get_alarm_state(AlarmName)
                    write_csv_file_report(ELBName,AlarmName,'ClassicELB','Success',alarm_state)
                except:
                    err = PrintException()
                    print(err)
                    stepName = Action + " Alarm"
                    write_csv_file(stepName,AlarmName,err)
                    alarm_state = get_alarm_state(AlarmName)
                    write_csv_file_report(ELBName,AlarmName,'ClassicELB',err,alarm_state)

            if Action == "disable":
                print(f"Disabling alarm_actions for ELB : { AlarmName }")
                try:
                    alarm_client.disable_alarm_actions(AlarmNames=[AlarmName])
                    alarm_state = get_alarm_state(AlarmName)
                    write_csv_file_report(ELBName,AlarmName,'ClassicELB','Success',alarm_state)
                except:
                    err = PrintException()
                    print(err)
                    stepName = Action + " Alarm"
                    write_csv_file(stepName,AlarmName,err)
                    alarm_state = get_alarm_state(AlarmName)
                    write_csv_file_report(ELBName,AlarmName,'ClassicELB',err,alarm_state)           
    except:
        err = PrintException()
        print(err) 
  
def get_alarm_state(alarm_name):
    client = boto3.client('cloudwatch',config=config)
    response = client.describe_alarms(
    AlarmNames=[
        alarm_name,
    ]
    )
    if response['CompositeAlarms'] != []:
        alarm_state = response['CompositeAlarms'][0]['StateValue']
        print("alarm_state : ",alarm_state)
    if response['MetricAlarms'] != []:
        alarm_state = response['MetricAlarms'][0]['StateValue']
        print("alarm_state : ",alarm_state)
    return alarm_state
  
       
def application_elb_alarm(Action,AlarmName,ALBTargetGroups,InstanceList,instanceIPs,alarmType):
    try:
        elb_client = boto3.client('elbv2',config=config)
        alarm_client = boto3.client('cloudwatch',config=config)
        elbInstancelist = []
        for alb_tg in ALBTargetGroups:
            targetGroups = elb_client.describe_target_groups(Names=[alb_tg])
            targetGroups = targetGroups['TargetGroups']
            for tg in targetGroups:
                targetGroupArn = tg['TargetGroupArn']
                elbTargetHealth = elb_client.describe_target_health(TargetGroupArn=targetGroupArn)
                for thd in elbTargetHealth['TargetHealthDescriptions']:
                    elbInstancelist.append(thd['Target']['Id'])
        # It will disable/enable ELB alarm even if one instance is part of ELB
        if any(item in InstanceList for item in elbInstancelist) or all(item in instanceIPs for item in elbInstancelist):
            print("\nType : ",alarmType)
            print("ELB Target Groups : ", ALBTargetGroups)
            print("ELB Alarm Name : ", AlarmName)
            print("All Target Group Instances are part of Stopping/Starting Schedule")
            if Action == "enable":
                print(
                    f"Enabling alarm_actions for ALB/NLB : { AlarmName }")
                try:
                    alarm_client.enable_alarm_actions(AlarmNames=[AlarmName])
                    alarm_client.set_alarm_state(AlarmName=AlarmName,StateValue='OK',StateReason='automation script after enabling alarm')
                    alarm_state = get_alarm_state(AlarmName)
                    write_csv_file_report(ALBTargetGroups,AlarmName,alarmType,'Success',alarm_state)
                except:
                    err = PrintException()
                    print(err)
                    stepName = Action + " Alarm"
                    write_csv_file(stepName,AlarmName,err)
                    alarm_state = get_alarm_state(AlarmName)
                    write_csv_file_report(ALBTargetGroups,AlarmName,alarmType,err,alarm_state) 
                
            if Action == "disable":
                print(
                    f"Disabling alarm_actions for ALB/NLB : { AlarmName }")
                try:
                    alarm_client.disable_alarm_actions(AlarmNames=[AlarmName])
                    alarm_state = get_alarm_state(AlarmName)
                    write_csv_file_report(ALBTargetGroups,AlarmName,alarmType,'Success',alarm_state)
                except:
                    err = PrintException()
                    print(err)
                    stepName = Action + " Alarm"
                    write_csv_file(stepName,AlarmName,err)
                    alarm_state = get_alarm_state(AlarmName)
                    write_csv_file_report(ALBTargetGroups,AlarmName,alarmType,err,alarm_state)    
    except:
        err = PrintException()
        print(err) 
              

def alarm_main(PatchInstallOnTagValue,action,patching_tag):      
    try:
        print("Alarm action : ", action)   

        ec2_client = boto3.client('ec2',region_name = region,config=config)
        alarm_client = boto3.client('cloudwatch',config=config)
        instancelist = []
        instanceIPs = []
        ec2_filter = [
                    {'Name':"tag:"+patching_tag, 'Values':[PatchInstallOnTagValue]}        
                    ]
        response = ec2_client.describe_instances(Filters=ec2_filter)
        for r in response['Reservations']:
            for instance in r['Instances']:
                instancelist.append(instance['InstanceId'])
                instanceIPs.append(instance['PrivateIpAddress'])  

        if instancelist:
            print(f'Found Instances that match ec2_filter: {ec2_filter}')
            print(instancelist)
            alarm_action(action,instancelist,instanceIPs,None)            
        else:
            raise Exception(f'No Instances found that match ec2_filter: {ec2_filter} . Hence, terminating execution....')
    except:
        print(PrintException())
        sys.exit(1)
        
        

def lambda_handler(event, context):
    global bucket_name
    global S3_directory_name, region
    global errorLog_Local_FullFileName
    global alarmReport_Local_FullFileName
    global patchJob_id
    global S3_Folder_Name
    Patching_Type = event['Patching_Type']
    bucket_name = event['S3_Bucket']
    S3_directory_name = event['S3_directory_name']   
    S3_Folder_Name = event['S3_Folder_Name'] 
    patchJob_id = S3_directory_name.split('/')[2]
    tagValue = event['PatchInstallOn']
    region = event['region']
    if Patching_Type == 'Standard':
        patching_tag = "PatchInstallOn"
    else:
        patching_tag = "AdhocPatchInstallOn"
    '''
    if "_BY_AY" in tagValue:
        action = "disable"
    else:
        action = "enable"
    '''

    x = re.search('_BY$', tagValue)
    if (x!=None):
        action = "disable"
    else:
        action = "enable"

    errorLogFileName = "Error_Logs_Patching_" + tagValue + ".csv"
    alarmReportFileName = "Alarms_Action_" + action + "_" + tagValue + ".csv"
    
    # local_Folder = "C:\\temp\\"
    local_Folder = "/tmp/"
    errorLog_Local_FullFileName = local_Folder + errorLogFileName
    alarmReport_Local_FullFileName = local_Folder + alarmReportFileName
    
    S3_folder = S3_Folder_Name + "/" + 'PATCHING/' + S3_directory_name
    errorLog_S3_FullFileName =  S3_folder + '/Error Logs/' + errorLogFileName   
    alarmReport_S3_FullFileName = S3_folder + '/AlarmsAction_' + action + '/' + alarmReportFileName    
    
    
    if (IsObjectExists(errorLog_S3_FullFileName)):
        download_file_from_S3_bucket(errorLog_Local_FullFileName,errorLog_S3_FullFileName)

    write_csv_file_report('Resource','Alarm Name', 'Alarm Type', 'Status','Alarm State')
    
    alarm_main(tagValue,action,patching_tag)    
    
    if os.path.exists(errorLog_Local_FullFileName):
        print("File Exists")
        upload_file_into_s3(errorLog_Local_FullFileName,errorLog_S3_FullFileName)
    
    upload_file_into_s3(alarmReport_Local_FullFileName,alarmReport_S3_FullFileName)
    
    jsonValues = {}
    jsonValues['Patching_Type'] = Patching_Type
    jsonValues['PatchInstallOn'] = tagValue
    jsonValues['S3_Bucket'] = bucket_name
    jsonValues['S3_directory_name'] = S3_directory_name
    jsonValues['app_action'] = "stop"
    jsonValues['S3_Folder_Name'] = S3_Folder_Name
    jsonValues['region'] = region
    print(jsonValues)
    return jsonValues
  
    
# simple test cases
if __name__ == "__main__":
    #event1 = {"Action": "enable"}
    event1 = {"PatchInstallOn": "WIN_TEST-NOV_21_2021_13_30_4HRS","Action": "enable",'S3_Bucket': 'dxc', 'S3_directory_name': 'NOV_2021/ap-south-1/patchJobId_90963df6-46b9-11ec-b2db-8c8caa2990d1',"S3_Folder_Name" : "test","region":"ap-south-1"}

    lambda_handler(event1, "")

