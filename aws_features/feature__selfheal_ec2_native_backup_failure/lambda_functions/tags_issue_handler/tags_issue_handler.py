"""
This Lambda function is used to collects collects all the 
tag and its value from SSM Parameter Store and checks those tags with the 
instance ID that is give to it as an input and returns the all the tags 
those are missing and if the input has key as "Flag" and 
its Value as "Fix" than it create those tags to that instance.

This Lambda is a part of Selfheal EC2 NativeBackupFailure

In Diagnosis state machine (dxcms_sh_nbf_sfn_diagnosis):
gets executed after - ReadBackupDetails State
On successful check, next state - CheckIAMRole is called.
On FAILURE, next State - TriggerNotificationSfnWError and NotifyForLambaFunctionFailure.

In Resolution state machine (dxcms_sh_nbf_sfn_resolution):
gets executed after - Start
On successful check, next state - IAMRoleRemediation is called.
On FAILURE, next State - TriggerNotificationSfnWError and NotifyForLambaFunctionFailure.
"""

import json
import boto3
import sys
import traceback
import os
from botocore.config import Config


config=Config(retries=dict(max_attempts=10,mode='standard'))


client=boto3.client('ec2', config=config)
ec2 = boto3.resource('ec2', config=config)
ssm_client = boto3.client("ssm", config=config)
ssm_Parameter = os.environ['ssm_Parameter']
#ssm_Parameter = '/DXC/EC2Backup-SelfHeal/InstanceTags'

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
        input = str(e)[:200]
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
    This function will return the 
    value stored in Parameter Store 
'''
def ssm_parameter():

    print("ssm_parameter Called")
    error = False
    try:
        get_response = ssm_client.get_parameter(Name=ssm_Parameter)
        value=json.loads(get_response['Parameter']['Value'])
        print (value)

    except Exception as e:
        # print(PrintException())
        print("Error ssm_parameter() - ",e)
        error = traceback.format_exc()
        print("Something went wrong while retriving data from SSM Store :(")
           
    return value, error

    
'''
    This Function compare the tags stored in Paramenter 
    store with the Tags that are present on Instance.
'''
def tag_checker(instance_id,tags_list):

    print("tag_checker Called")
    tags_not_present={}
    superFlag = False
    error = False
    try:
        ec2instance = ec2.Instance(instance_id)
        ec2_tag_list = ec2instance.tags
        print(ec2_tag_list)
    except:
        error = traceback.format_exc()
        
    else:    
        if ec2_tag_list != None:
            try:
                
                
                for tag in tags_list:
                    flag=False
                    
                    for tags in ec2_tag_list:
        
                        if tags['Key'] == str(tag['Key']):
                            print("Tag Present: "+tag['Key'])
                            flag=True
                            break
        
                    if not flag:
                        superFlag = True
                        tags_not_present.update({str(tag['Key']) : str(tag['Value'])})
                        print("Tag not Present: "+tag['Key'])
        
        
                if superFlag:
                    print(str(tags_not_present.keys)+' instance_id :'+instance_id)
                else:
                    print('tags are present in instance_id :'+ instance_id)
            
            except Exception as e:
                # print(PrintException())
                print("Error tag_checker() - ",e)
                error = traceback.format_exc()
                print("Something went wrong while retriving tags from Instance ")
        else:
            superFlag = True
            for tag in tags_list:
                tags_not_present.update({str(tag['Key']) : str(tag['Value'])})
                
    return superFlag, tags_not_present, error


'''
    This function will create tags from 
    the dictionary called missing_tags
'''
def tag_creator(instance_id, missing_tags):

    print("tag_creator Called")
    tags = []
    error = False
    status = False
    for key in missing_tags:       
        tags.append({
            "Key" : key, 
            "Value" : missing_tags[key]
        })
                
    if tags:
        try:
            response = client.create_tags(
                Resources = [instance_id],
                Tags= tags
            )
            print(response)
            print("Added Tag: "+ str(tags))
        except Exception as e:
            # print(PrintException())
            print("Error tag_creator() - ",e)
            print("While Fixing tags Something went wrong while fixing tags :(")
            error = traceback.format_exc()
            status = False
        else:
            print("Tags Fixed Successfully :)")
            status = True
    
    return status, error


'''
    This function checks if particular key 
    is present or not with particular value
'''
def checkKey(dict, key):

    print("checkKey Called")  
    if key in dict.keys():
        if dict[key] == 'Fix':
            return True

    return False


def lambda_handler(event,context):
    global task_token, instance_id

    print("input recieved to this script - " + str(event))
    task_token = event["token"]
    event = event["Payload"]
    instance_id = event["instance_id"]
    try:
        error_status = False
        tags_list, error_status=ssm_parameter()
        if not error_status:
            event["Instance_Tags_Status"] = ''
            
            
            status, tags_not_present, error_status = tag_checker(instance_id,tags_list)
            if not error_status:
                print('Status :' + str(status))
                event["Missing_Tags"] = list(tags_not_present)
            
                if status:
                    if checkKey(event, "Flag"):
                        print("Initiating Tag/s Fixing.......")
                        flag, error_status = tag_creator(instance_id, tags_not_present)
                        if not error_status:
                            if flag:
                                event["Instance_Tags_Status"] = "Present" 
                                event["Missing_Tags"] = [] 
                            else:
                                event["Instance_Tags_Status"] = "Not_Present"      
                        else:
                            raise Exception(f"Error tag_creator() - Error while finding/creating tags on {instance_id}")
                    else:
                        print("")
                        event["Instance_Tags_Status"] = "Not_Present"
                else:
                    event["Instance_Tags_Status"] = "Present"
            else:
                raise Exception(f"Error tag_checker() - Error while checking tags for instance {instance_id}") 
        else:
            raise Exception("Error ssm_parameter() - Error while reading ssm parameter")        
        if not error_status:    
            print(event)
            return success_token(event,task_token)
    except Exception as e:
        # print(PrintException())
        print("Error lambda_handler() - ",e)
        if not error_status:
            error_status = traceback.format_exc()
        input = str(e)[:200]
        return failure_token(task_token, input, error_status)