"""
This lambda is creating ExecutionsSucceeded and ExecutionsTimedOut alarms for tagged stepfunctions. 
sample input : 
                {
                    "alarm_action": "arn:aws:sns:ap-southeast-1:567529657087:sample_sns_topic",
                    "data_points": 1,
                    "disable_static_alarm": False,
                    "evalution_period": 1,
                    "expression": "ANOMALY_DETECTION_BAND(m1, 2)",
                    "metric_name": "ExecutionsSucceeded/ExecutionsTimedOut",
                    "s3_bucket": "dxc.customer.config-567529657087-ap-southeast-1"
                }
"""
import boto3
from botocore.config import Config
import os

config=Config(retries=dict(max_attempts=10,mode='standard'))

dynamodb_resource = boto3.resource('dynamodb',config=config)

cloudwatch = boto3.client('cloudwatch',config=config)

stepfunction_client = boto3.client('stepfunctions')

table_name = os.environ['table_name']

def get_data(Metric_name):
    table = dynamodb_resource.Table(table_name)
    response = ''
    try:
        item_dict = { 
        'Metric Name': Metric_name
        } 
        response = table.get_item(
            Key=item_dict
        )
        print(response)
    except Exception as e:
        response = ''
        print("Error get_data() - ",e)
    return response

def create_ad_alarms(machinearn,machinename,band,datappoints,evalution_period,period,Metric_name,topic_arn):
    try:
        AlarmName = 'ad_alerts_'+Metric_name+"_"+machinename
        cloudwatch.put_metric_alarm(
            AlarmName=AlarmName, 
            AlarmDescription="this is dynamic alarm",
            ActionsEnabled=True,
            AlarmActions=[
                topic_arn],
            EvaluationPeriods=evalution_period,
            DatapointsToAlarm=datappoints,
            ComparisonOperator='GreaterThanUpperThreshold',
            TreatMissingData='missing',
            Metrics=[{
                'Id': 'm1',
                'MetricStat': {
                    'Metric': {
                        'Namespace': 'AWS/States',
                        'MetricName': Metric_name,
                        'Dimensions': [{
                            'Name': 'StateMachineArn',
                            'Value': machinearn
                        }]
                    },
                    'Period': period,
                    'Stat': "Sum"
                },
                'ReturnData': True
            }, {
                'Id': 'ad1',
                'Expression': 'ANOMALY_DETECTION_BAND(m1, '+band+')',
                'ReturnData': True
            }],
            ThresholdMetricId='ad1'
        )
        print("alarm created for ",machinename)

    except Exception as e:
        AlarmName = ''
        print("unable to proceed : ",e)
    return AlarmName
        
def get_state_machines(response):
    statemachinearns = []
    statemachinenames = []
    try:
        for states in response['stateMachines']:
            response = stepfunction_client.list_tags_for_resource(
                resourceArn=states['stateMachineArn']
            )
            for tag in response['tags']:
                if tag['key'] == 'adalarm' and tag['value'] == 'true':
                    print(states['name'])
                    response = stepfunction_client.list_executions(stateMachineArn=states['stateMachineArn'])
                    if len(response['executions']) > 0:
                        statemachinearns.append(states['stateMachineArn'])
                        statemachinenames.append(states['name'])
    except Exception as e:
        print("Error in get_state_machines() ",e)
    return statemachinearns,statemachinenames

def lambda_handler(event, context):
    try:
        print('Received event is ',event)
        alarm_names = []
        statemachinenames= []
        paginator = stepfunction_client.get_paginator('list_state_machines')
        response_iterator = paginator.paginate(
            PaginationConfig={
                'MaxItems': 200
            }
        )
        for value in response_iterator:
            statemachinearns,statemachinenames = get_state_machines(value)
            metric_names = ['ExecutionsAborted','ExecutionsTimedOut']
            for metric_name in metric_names:
                i=0
                response = get_data(metric_name)
                band = response['Item']['Band']
                datappoints = int(response['Item']['Data Points'])
                evalution_period = int(response['Item']['Evalution Period'])
                period = int(response['Item']['Period'])
                Metric_name = response['Item']['Metric Name']
                topic_arn = response['Item']['SNS Topic ARN']
                for machine in statemachinearns:
                    alarm = create_ad_alarms(machine,statemachinenames[i],band,datappoints,evalution_period,period,Metric_name,topic_arn)
                    i=i+1   
                    alarm_names.append(alarm)
        event= {}
        event['State_Machines'] = statemachinenames
        event['Alarms'] = alarm_names
    except Exception as e:
        print("Error lambda_handler() - ",e)
    return event