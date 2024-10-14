'''
    This Lambda function is a part of feature__selfheal_foundation stepfuction.
    Here we are fetching the API Credentials and URL from SecreteManager and we are making the header as well as body for creating the event
    After we are using the post to create event and we are giving header and body to the API Request.
    It will evalute the data and it will create and return the event number.
    Input Required:
    {
      
      "resource_id": "i-03e74d54cd95bc864",
      "Backup_Validation_Status": false,
      "short_message":"",
      "long_message":""
    }

    In dxcms_sh_sfn_notification,
    On successful check, Creates Snow Incident.
    On FAILURE, next State CreateSnowIncidentError and then NotifyForLambdaFunctionFailure.
'''
import boto3
import os, sys
import json
import uuid
import traceback
from botocore.config import Config
import datetime


config=Config(retries=dict(max_attempts=10,mode='standard'))

secmgr_client = boto3.client('secretsmanager',config=config)
region = os.environ['AWS_REGION']
sns_client = boto3.client('sns',config=config)
dynamodb_client =  boto3.client('dynamodb',config=config)
currentDT = datetime.datetime.now()
Date_time= currentDT.strftime("%Y%m%d_%H%M%S")
topic_arn = os.environ['SNS_TOPIC']
table_name = os.environ['table_name']

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

def lambda_handler(event, context):
    global task_token, resource_id, resource_type
    print("input recieved to this script - " + str(event))
    error = False
    task_token = event["token"]
    event = event["Payload"]
    if ("resource_id" in event):
        resource_id = event["resource_id"]
    else:
        resource_id = event["instance_id"]
    try:
        resource_type = event["resource_type"]
    except:
        resource_type = ""
    try:
        Request_id = context.aws_request_id
        severity_dict = { "1":"Critical", "2":"Major", "3":"Minor", "4":"Warning"}
        if(event["Resolution_Validation"]==True):
            priority = "4"
            Severity = severity_dict[priority]
        else:
            if "selfHealJobId" in event:
                priority = fetch_priority(event["selfHealJobId"])
            else:
                priority = "3"
            Severity = severity_dict[priority]

        if ("Event" in event):
            if (event["Event"] in ["EC2CloudWatchAlarms", "LambdaAnomalyDetection"]):
                API_message, error = cw_lad_alarms_EventBody(event,Request_id,priority,Severity)
                if error:
                    raise Exception("Error while forming api message body. Please check payload passed. snow incident not created")
            else:
                new_state_reason = 'AWS SelfHeal solution: ' + str([{'ResourceId':resource_id, 'Notification':'false','ResourceType':resource_type}])
                API_message, error = EventBody(event,Request_id,priority,Severity,new_state_reason,resource_id)
                if error:
                    raise Exception("Error while forming api message body. Please check payload passed. snow incident not created")
        else:
            new_state_reason = 'AWS SelfHeal solution: ' + str([{'ResourceId':resource_id, 'Notification':'false','ResourceType':resource_type}])
            API_message, error = EventBody(event,Request_id,priority,Severity,new_state_reason,resource_id)
            if error:
                raise Exception("Error while forming api message body. Please check payload passed. snow incident not created")
        
        event_status = send_to_FtCommonServiceNow(API_message)
        if event_status != "SUCCESS":
            raise Exception("Error while creating incident/event. SNow Incident not created.")
        event["Event_status"] = event_status
        
        return success_token(event,task_token)
    except Exception as e:
        print("Error lambda_handler() - ", e)
        if not error:
            error = traceback.format_exc()
        return failure_token(task_token, str(e)[:200], error)

def event_key():

    key = str(uuid.uuid1())

    return key

def fetch_priority(selfHealJobId):
    try:
        response = dynamodb_client.get_item(
            TableName=table_name,
            Key={'selfHealJobId': {'S': selfHealJobId}}
        )
        priority = response['Item']['Priority']['S']
        print(f"priority: {priority}")
        return priority
    except Exception as e:
        print("Error fetch_priority() - ",e)
        print(f"error reading 'Priority' from table {table_name} with key selfHealJobId: {selfHealJobId}")
        print(f"taking fallback priority as '3'.")
        priority = '3'
        return priority


def EventBody(event,Request_id,priority,Severity,new_state_reason,resource_id):
    body = {}
    error = False
    try:
        short_description = event["short_message"]
        description = event["long_message"]
        account_id = event["account_id"]
        key=event_key()
        domain_name, error = get_ssm_parameter_value("/DXC/ServiceNow/DomainName")
        if error:
            raise Exception("error while reading /DXC/ServiceNow/DomainName ssm parameter")
        
        body = {
                "EventList":[{
                        "Trigger":{
                            "Dimensions":[{"name": "InstanceId","value": resource_id}]
                        },
                        "AWSAccountId":account_id,
                        "NewStateReason": new_state_reason,
                        "eventsourcesendingserver":"AWS Selfheal",
                        "eventsourceexternalid":Request_id,
                        "severity":Severity,
                        "title":short_description,
                        "longDescription":description,
                        "category":"AWS SelfHeal",
                        "key":key,
                        "domainName":domain_name,
                        "application": "feature__selfheal_foundation",
                        "eventsourcecreatedtime": Date_time,
                        "PriorityData" : {
                            "Priority": priority
                        }    
                    }]
            }
        print("EventBody returned")
    except Exception as e:
        print("Error EventBody() - ", e)
        error = traceback.format_exc()
    finally:
        return body,error
    
def cw_lad_alarms_EventBody(event,Request_id,priority,Severity):
    body = {}
    error = False
    try:
        short_description = event["short_message"]
        try:
            new_state_reason = event["long_message"]["NewStateReason"]
        except:
            new_state_reason = 'AWS SelfHeal solution: ' + str([{'ResourceId':event["resource_id"], 'Notification':'false','ResourceType':resource_type}])
        if(isinstance(event["long_message"],str)):
            description = event["long_message"]
        else:
            description = json.dumps(event["long_message"])
        account_id = event["account_id"]
        alarm_name = event["AlarmName"]
        key=event_key()
        domain_name, error = get_ssm_parameter_value("/DXC/ServiceNow/DomainName")
        if error:
            raise Exception("error while reading /DXC/ServiceNow/DomainName ssm parameter")

        body = {
                "EventList":[{
                        "AlarmName":alarm_name,
                        "AWSAccountId":account_id,
                        "NewStateReason": new_state_reason,
                        "eventsourcesendingserver":"AWS Selfheal",
                        "eventsourceexternalid":Request_id,
                        "severity":Severity,
                        "title":short_description,
                        "longDescription":description,
                        "category":"AWS SelfHeal",
                        "key":key,
                        "domainName":domain_name,
                        "application": "feature__selfheal_foundation",
                        "eventsourcecreatedtime": Date_time,
                        "PriorityData" : {
                            "Priority": priority
                        }    
                    }]
            }
        if (event["Event"] == "EC2CloudWatchAlarms"):
            trigger = event["Trigger"]
            body["EventList"][0]["Trigger"] = trigger
        print("EventBody returned")
    except Exception as e:
        print("Error cw_lad_alarms_EventBody() - ", e)
        error = traceback.format_exc()
    finally:
        return body,error

def send_to_FtCommonServiceNow(API_message):
    except_reason = None
    try:
        print('API message is :', API_message)
        sns_client_response = sns_client.publish(
            MessageStructure='json',
            Message=json.dumps(
                        {'default': json.dumps(API_message)}
                    ),
            TopicArn=topic_arn
        )
        print("sns_client_response is: ", sns_client_response)
    except Exception as e:
        print('Error:send_to_FtCommonServiceNow()-', e)
        except_reason = 'Error in send_to_FtCommonServiceNow' + str(traceback.format_exc()) 
    if except_reason is not None:
        return except_reason
    else:
        return 'SUCCESS' 

def get_ssm_parameter_value(parameter_name):
    print("get_ssm_parameter_value() triggered")
    ssm_client = boto3.client('ssm', config=config)
    error_status = False
    try:
        response = ssm_client.get_parameter(
            Name = parameter_name
        )
        return response['Parameter']['Value'],error_status
    except Exception as e:
        print("Error get_ssm_parameter_value()- ",e)
        return "",e       