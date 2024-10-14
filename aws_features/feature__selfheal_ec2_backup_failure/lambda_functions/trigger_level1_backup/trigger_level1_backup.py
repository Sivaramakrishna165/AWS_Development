"""
    This Lambda function is used to find all the associated Volume IDs and 
    then triggers a Level 1 backup for all those Volumes.

    In dxcms_sh_bf_sfn_execute_backup state machine(TriggerLevel1Backup)
    gets executed after CheckcmdStatus state.

    Input event of the lambda function is:
    {
        "instance_id":"<instance-id>", 
        "selfHealJobId": "<selfHealjobid>"
    }

    In executebackup state machine,
    On successful check, next state - waitstate to checksnapshotbackupstatus is called.
    On FAILURE, next State TriggerLevel1BackupError and then NotifyForLambaFunctionFailure.
    
"""

#instance_backup_creater

import json
import boto3
import sys
import os
import datetime
import traceback
from boto3.dynamodb.conditions import Key
from botocore.config import Config


config=Config(retries=dict(max_attempts=10,mode='standard'))


'''
    Declaration of Global Variables
'''
table_name = os.environ['table_name']
# table_name = 'Ft_Dxcms_EC2_Backup_SelfHeal'
lamda_function = os.environ['sns_lamda_function']


client = boto3.client('ec2', config=config)
dynamodb = boto3.resource('dynamodb', config=config)


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
    This function is creates snapshot of all the volume id 
    passed to it as a list and also attach following tags: 
    Name, VolumeID, DeleteOn 
'''
def create_snapshot(volume_ids, instance_id):

    print("create_snapshot called")
    dictt = {}
    error = False
    try:
        for volume in volume_ids:
            tag_list = get_tag(instance_id, volume)
            print("Tag List: "+ str(tag_list))
            response = client.create_snapshot(
                Description = 'Basic EBS snapshot of volume',
                VolumeId=volume,
                DryRun=False
            )
            print("Snapshot is created for the volume id " + str(volume)+" === "+response['SnapshotId'])
            dic = {str(volume):str(response['SnapshotId'])}
            response = client.create_tags(
                DryRun=False,
                Resources=[
                    response['SnapshotId'],
                ],
                Tags= tag_list
            )
            dictt.update(dic)
            
            print("")
    except Exception as e:
        # print(PrintException())
        print("Error create_snapshot() - ",e)
        error = True
        print("Error during create_snapshot")
    
    print(str(dictt))
     
    return dictt, error
    

'''
    This function creates and retuns the list of tags that will 
    be attached to the snapshot created following tags it 
    creates: Name, VolumeID, DeleteOn
'''
def get_tag(instance_id, volume_id):
    print("get_tag called")
    tag_list = []
    tag1 = {}
    tag2 = {}
    tag3 = {}
    RetentionPeriod = ''
    ec2 = boto3.resource('ec2', config=config)
    ec2instance = ec2.Instance(instance_id)
    flag=False
    for tag in ec2instance.tags:
        if tag['Key'] == 'RetentionPeriod':
            RetentionPeriod = tag['Value']
            flag=True
            break
    
    if flag:
        today = datetime.datetime.now()
        deleteOn = today + datetime.timedelta(days=int(RetentionPeriod))
        deleteOn = deleteOn.strftime("%Y-%m-%d")
        # print(deleteOn)
    else:
        deleteOn = '-'

    tag1['Key'] =   'Name'
    tag1['Value'] = 'InstanceId: ' + instance_id
    
    tag2['Key'] =   'VolumeID'
    tag2['Value'] = volume_id
    
    tag3['Key'] =   'DeleteOn'
    tag3['Value'] = str(deleteOn)

    tag_list.append(tag1)
    tag_list.append(tag2)
    tag_list.append(tag3)

    #print(tag_list)
    return tag_list


'''
    This function is writing data to DynamoDB
'''
def update_item_dynamoDB(selfHealJobId,dictt):
    print("update_item_dynamoDB called")
    try:
        dynamodb = boto3.resource('dynamodb', config=config)
        dataItem = {}

        patch_table = dynamodb.Table(table_name)
        patch_table.update_item(
            Key={'selfHealJobId': selfHealJobId},
            
            UpdateExpression="set SelfHealBackupOutput=:s",
            
            ExpressionAttributeValues={':s': str(dictt)},
            ReturnValues="UPDATED_NEW"
        )
    except Exception as e:
        print("error during update_item_dynamoDB() -",e)
        print("Error Occured While Updating Table")
        input = {"error" : str(e), "resource_id" : instance_id, "resource_type" : "EC2 Instance"}
        failure_token(task_token, input, traceback.format_exc())
    else:
        print("Successfully Updated SelfHealBackupOutput value")


'''
    This Function is getting the instance id 
    and volume id list from the DynamoDB 
'''
def get_backup_data(selfHealJobId):
    print("get_backup_data called")
    table = dynamodb.Table(table_name)
    volume_Id = []
    error_status = False
    try:
        
        response = table.scan()

        dynamodb_resource = boto3.resource('dynamodb')
        table = dynamodb_resource.Table(table_name)

        if selfHealJobId is not None:
            filtering_exp = Key('selfHealJobId').eq(selfHealJobId)
            item = (table.query(KeyConditionExpression=filtering_exp)['Items'][0])
            volume_Id = item['Volume ID'][1:-1].replace("'", "").replace(" ", "").split(",")
            print(f"volume_Id={volume_Id}")

        return volume_Id, error_status

    except Exception as e:
        # print(PrintException())
        print("Error get_backup_data() - ",e)
        error_status = traceback.format_exc()
        return volume_Id, error_status

'''
    This Function calls Lambda Function 
    with event data as a JSON input
'''
def lambda_function(event_data, func_name):
    print("lambda_function called")
    lambda_client = boto3.client('lambda', config=config)
    response = lambda_client.invoke(
        FunctionName = func_name,Payload=json.dumps(event_data)
    )


def lambda_handler(event,context):
    global task_token, instance_id

    print("input recieved to this script - " + str(event))
    task_token = event["token"]
    event = event["Payload"]
    selfHealJobId = event["selfHealJobId"]
    instance_id = event["instance_id"]
    error_status = False
    try:
        volume_Id_list, error_status = get_backup_data(selfHealJobId)
        # volume_Id_list = get_volumeID_list(instance_id)
        print(f"{volume_Id_list}")
        if not error_status:
            dictt, status = create_snapshot(volume_Id_list,instance_id)
            if not status:
                update_item_dynamoDB(selfHealJobId,dictt)
                lambda_function(event, lamda_function)
                event["SelfHealBackupOutput"] = dictt
                event["status"] = "pending"
                event["count"] = 8
                event["backup_level_taken"] = "1"
                print(event)
                return success_token(event,task_token)
            else:
                raise Exception("Error while creating level 1 snapshots.") 
        else:
            raise Exception("Error get_backup_data() - Error while reading volume ids.") 
    except Exception as e:
        print("Error lambda_handler() - ",e)
        if not error_status:
            error_status = traceback.format_exc()
        input = {"error" : f"Error lambda_handler() - {str(e)}", "resource_id" : instance_id, "resource_type" : "EC2 Instance"}
        return failure_token(task_token, input, error_status)


if __name__ == "__main__":
    event1 = {"selfHealJobId":"selfHealJobId_e4453cd9-f5df-11ec-a298-75505dee31e0", "instance_id": "i-03e74d54cd95bc864"}   
                #   i-03f2a963369545021
    lambda_handler(event1, "")