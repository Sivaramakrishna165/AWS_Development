"""
    This Scripts call the step function whose ARN
    is given in Enivronment Variable and Json data 
    that we recieve as an input.

    Input Example: {}
"""

import json
import boto3
import os,sys
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))

def PrintException():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    captureErr = "Line No. : " + str(lineno) + " | ERROR: " + str(exc_obj)
    return captureErr

'''
    This function is calling a stepfunction using 
    Stepfunction ARN and JSON Data as an Input
'''
def stepfunction(step_arn, json_data):
    print("Stepfunction Called")
    statefunction = boto3.client('stepfunctions', config=config)
    try:
        response = statefunction.start_execution(
                            stateMachineArn = step_arn,
                            input = json.dumps(json_data)
                        )
    except:
        print(PrintException())
        print("Error during stepfunction call")
    else:
        print("Triggered Successfully")

def lambda_handler(event, context):
    # TODO implement
    event = json.loads(event['Records'][0]['Sns']['Message'])
    payload_flag = False
    step_arn = os.environ['step_arn']
    bf_payload_keys = set(['VolumeIds', 'LatestBackup', 'EventDate', 'Event', 'IncidentPriority', 'region'])
    cs_payload_keys = set(['OldStateValue', 'NewStateValue', 'EventDate', 'Event', 'IncidentPriority', 'region'])
    cw_paylaod_keys = set(['logGroupName', 'logStreamName', 'OldStateValue', 'NewStateValue', 'EventDate', 'Event', 'IncidentPriority', 'region'])
    
    try:
        if('lambda' in event):
            if(isinstance(event['lambda'],str)):
                event = json.loads(event['lambda'])
            else:
                event = event['lambda']
        
        print('Event recieved - ', event)
        if ('Event') in event:
            usecase = event['Event']
            print (usecase)
        else:
            raise Exception("Wrong payload passed")
        
        if usecase == "BackupFailure":
            if bf_payload_keys.issubset(event.keys()):
                payload_flag = True
        elif usecase == "CrowdStrikeFalconAgentFailure":
            if cs_payload_keys.issubset(event.keys()):
                payload_flag = True
        elif usecase == "CloudWatchAgentLogFailure":
            if cw_paylaod_keys.issubset(event.keys()):
                payload_flag = True
        else:
            raise Exception("Wrong Event in payload. Expected Values : BackupFailure | CrowdStrikeFalconAgentFailure | CloudWatchAgentLogFailure")
        
        if ('InstanceId' in event) or ('instanceId' in event):
            pass
        else:
            raise Exception("Wrong payload passed")
        
        if payload_flag:
            stepfunction(step_arn, event)
            print('Step function executed - ', step_arn)
        else:
            raise Exception("wrong payload passed.")
        
        return event
    
    except Exception as e:
        print("Error lambda_handler() - ", e)
        print("=======================")
        print("Payload Recived: ",event)

event1 = {}

if __name__ == "__main__":
    lambda_handler(event1,"")