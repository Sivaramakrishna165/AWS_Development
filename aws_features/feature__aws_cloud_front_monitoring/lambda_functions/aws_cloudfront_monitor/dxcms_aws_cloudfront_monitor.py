'''
Lambda function does the below
    Reads the Alarms from 'AWSCloudFrontMonitoring' item available in DDB - AccountFeatureDefinition
    And creates CW alarms for CloudFront service
NOTE: CloudFront is a Global service, so this Feature/Offerings should be deployed ONLY in us-east-1
'''

import os
import boto3
import json
import urllib.parse
import http.client
from boto3.dynamodb.conditions import Key,Attr
from botocore.config import Config
from dynamodb_json import json_util as ddb_json

dim_invalid_values = ['','<TO BE FILLED>']
commonIncidentTopic = os.environ['CommonIncidentTopic']
sns_topic= os.environ['NotifyEmailTopic'] #Email topic for sending report info
region=os.environ['STACK_REGION']
acc_id=os.environ['EXECUTION_ACCOUNT']

config = Config(retries=dict(max_attempts=10,mode='standard'))
cloudwatch_client = boto3.client("cloudwatch",config=config)
dynamodb_client = boto3.client("dynamodb",config=config)
sns_client= boto3.client("sns",config=config)


def send_response(request, response, status=None, reason=None):
    if status is not None:
        response['Status'] = status
    if reason is not None:
        response['Reason'] = reason
    if 'ResponseURL' in request and request['ResponseURL']:
        try:
            url = urllib.parse.urlparse(request['ResponseURL'])
            body = json.dumps(response)
            https = http.client.HTTPSConnection(url.hostname)
            https.request('PUT', url.path + '?' + url.query, body)
            print('Response sent successfully')
        except:
            print("Failed to send the response to the provided URL")
    return response

def alarm_check(alarm_name):
    try:
        response = cloudwatch_client.describe_alarms(AlarmNamePrefix=alarm_name)  
        alarmlist = (response.get('MetricAlarms')[0].get('AlarmName'))
        print('"{}" alarm already exists'.format(alarm_name)) 
        return alarmlist    
    except:
        print('"{}" alarm NOT exists'.format(alarm_name)) 
        return

#Executing the function to create the Alarms.
def create_alarm(**param):
    try:
        cloudwatch_client.put_metric_alarm(**param)
        print("CloudWatch alarm creation SUCCESS - ",param['AlarmName'])
        return "CloudWatch alarm creation SUCCESS"
    except Exception as e:
        exp = 'Error in creating the cloudwatch alarm {}'.format(e)
        print(exp)
        return exp

def publish_msg(topic,text,msg,subject):
    try:
        text+=json.dumps(msg,indent=4)
        sns_params = {
                    'Message': text,
                    'Subject': subject,
                    'TopicArn': topic
                        }
        sns_client.publish(**sns_params)
        print("Report Published SUCCESSFULLY to ",topic)
    except Exception as e:
        print("Error-publish_msg",e) 
        
def handler(event, context):
    try:
        print('Event Received - ', event)
        response = {}
        response['Status'] = 'SUCCESS'
        response['Reason'] = 'See the details in CloudWatch Log Stream: ' + context.log_stream_name
        response['PhysicalResourceId'] = context.log_stream_name
        response['StackId'] = event['StackId']
        response['RequestId'] = event['RequestId']
        response['LogicalResourceId'] = event['LogicalResourceId']
        response['NoEcho'] = False

        if (event['RequestType'] in ['Create','Update']) and ('ServiceToken' in event):
            try:
                #Fetching the details from DynamoDB.
                dynamodb_response = dynamodb_client.get_item(TableName='AccountFeatureDefinitions',Key={"Feature":{'S':"AWSCloudFrontMonitoring"}}, ConsistentRead=True)
                parsed_item = ddb_json.loads(dynamodb_response)
                alarms = parsed_item["Item"]["Alarms"]
                report={}
                success_count=0
                failure_count=0

                for alarm in alarms:
                    try:
                        print(alarm)
                        create_alarm_result = None
                        bln_alarm_check_result = False
                        bln_valid_dim = True
                        bln_cloudfront_host = False
                        alarm_params = {}
                        alarm_name_space=alarms[alarm]['Namespace'].lower().replace("/","")
                        dimlist={}
                        for dim in alarms[alarm]['Dimensions']:
                            if dim['Value'].upper() in dim_invalid_values:
                                bln_valid_dim = False
                            dimlist[dim['Name']]=dim['Value']
                        
                        alarm_Dimensions = ''
                        if('DistributionId' in dimlist):
                            alarm_Dimensions='-'.join([dimlist['DistributionId'],dimlist['Region']])
                            bln_cloudfront_host = True

                        if('App' in dimlist):
                            alarm_Dimensions='-'.join([dimlist['App']])

                        alarm_name='-'.join(["dxcms",alarm_name_space,alarms[alarm]['MetricName'],alarm_Dimensions])
                        
                        if(not bln_valid_dim):
                            raise Exception('Invalid Dimensions {}'.format(alarms[alarm]['Dimensions']))
                        
                        if(region != 'us-east-1' and bln_cloudfront_host):
                            raise Exception('Invalid region - {}, please deploy DXC Managed Services in us-east-1 to create alarms'.format(region))
                        
                        bln_alarm_check_result=alarm_check(alarm_name)
                        
                        if not bln_alarm_check_result:
                            alarm_params['AlarmName']=alarm_name
                            alarm_params['Namespace']=(alarms[alarm]['Namespace'])
                            alarm_params['MetricName']=(alarms[alarm]['MetricName'])
                            alarm_params['Dimensions']=(alarms[alarm]['Dimensions'])
                            alarm_params['AlarmActions']=[commonIncidentTopic]
                            alarm_params['Statistic']=(alarms[alarm]['Statistic'])
                            alarm_params['Period']=int((alarms[alarm]['Period']))
                            alarm_params['EvaluationPeriods']=int((alarms[alarm]['EvaluationPeriods']))
                            alarm_params['ComparisonOperator']=(alarms[alarm]['ComparisonOperator'])
                            alarm_params['Threshold']=int(alarms[alarm]['Threshold'])
                            
                            create_alarm_result = create_alarm(**alarm_params)
                    except Exception as e:
                        print("Error-",e)
                        create_alarm_result=str(e)
                    finally:
                        if not bln_alarm_check_result:
                            if 'SUCCESS' in create_alarm_result:
                                success_count+=1
                            else:
                                failure_count+=1
                            report[alarm_name]={}
                            report[alarm_name]['Status']=create_alarm_result
                            report[alarm_name]['Configurations']=alarm_params

                if report:
                    text="AWS CloudFront Monitoring, create CW alarms report:\n\n"
                    text+="Sucess: "+str(success_count)+"\nFailed: "+str(failure_count)+"\n\nReport Information:\n\n"
                    print("Alarms creation report - ",report)
                    subject= 'DXCMS AWS CloudFront Monitoring, CW Alarms CREATE report. account - '+ str(acc_id) + ' region ' + region
                    # report=json.dumps(report)
                    publish_msg(sns_topic,text,report,subject)

                send_response(event, response, status='SUCCESS', reason='Lambda Completed')
                
            except Exception as e:
                print('Error', e)
                response['Error'] = str(e)
                send_response(event, response, status='FAILED', reason=str(e))

        if (event['RequestType'] in ['Delete']) and ('ServiceToken' in event):
            send_response(event, response, status='SUCCESS', reason='Delete event received')

        return {
            'statusCode': 200,
        }
    except Exception as e:
        print('Lambda Execution Error ',e)                        