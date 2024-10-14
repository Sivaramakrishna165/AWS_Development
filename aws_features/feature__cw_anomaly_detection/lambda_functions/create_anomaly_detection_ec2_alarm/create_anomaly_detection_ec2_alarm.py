"""
    This script will create anomaly alarms based on the adalarm tags.
    It doesn't require any input to trigger this lambda
"""
import boto3
import csv
import os
import io
from datetime import date
from datetime import datetime
from botocore.config import Config
config=Config(retries=dict(max_attempts=10,mode='standard'))

table_name = os.environ['table_name']
customer_name = os.environ['customer_name']
region = os.environ['AWS_REGION']

dynamodb_resource = boto3.resource('dynamodb',config=config)
s3_client = boto3.client('s3',config=config)

def ssm_parameter(name):
    result = ""
    try:
        ssm = boto3.client('ssm',config=config)
        response = ssm.get_parameter(
            Name = name,
            WithDecryption=True
        )
        result=response['Parameter']['Value']
    except Exception as e:
        print("error in ssm parameter",e)
    return result

def anomaly_report(alarm_name,instance_id,metric_name,writer,customer,account_id):
    try:
        print("Start creating Anomaly report")
        today = date.today()
        writer.writerow([
            customer,
            account_id,
            region,
            instance_id,
            alarm_name,
            metric_name,
            today
            ])
    except Exception as e:
        print("Error in anomaly_report() - ",e)

def get_static_alarms():
    cloudwatch = boto3.client('cloudwatch')
    # Describe alarms for the specified instance and metric
    paginator = cloudwatch.get_paginator('describe_alarms')
    
    response_iterator = paginator.paginate()
    alarm_details = []
    try:
        for value in response_iterator:
            metrics = value['MetricAlarms']
            for metric in metrics:
                alarm_name = metric['AlarmName']
                if 'DiskUtilAlarm' in alarm_name or 'Disk1UtilAlarm' in alarm_name or 'Disk2UtilAlarm' in alarm_name:
                    alarm_details.append(alarm_name)
    except Exception as e:
        print("Error in get_static_alarm() - ",e)
    return alarm_details
    
def get_alarms(alarms,instance_id):
    cloudwatch = boto3.client('cloudwatch')

    # Describe alarms for the specified instance and metric
    paginator = cloudwatch.get_paginator('describe_alarms')
    
    response_iterator = paginator.paginate(AlarmNames=alarms)
    # response = cloudwatch.describe_alarms(AlarmNames=alarms)

    details = []
    try:
        for response in response_iterator:
            for alarm in response['MetricAlarms']:
                Dimensions = alarm['Dimensions']
                for dimension in Dimensions:
                    if dimension['Name'] == 'InstanceId':
                        if dimension['Value'] == instance_id:
                            details.append(Dimensions)
    except Exception as e:
        print("Error in get_alarm() - ",e)
    return details

def create_anomaly_alarm(instance_id,evalution_period,datappoints,alarm_action,expression,metric_name,namespace,writer,customer,account_id):
    AlarmName=''
    Dimensions = ''
    if metric_name == 'MemoryUtilization' or metric_name == "Memory % Committed Bytes In Use":
        AlarmName='ad_alerts_memory_'+instance_id
        Dimensions = [[{
                    'Name': 'InstanceId',
                    'Value': instance_id
                }]]
    elif metric_name == 'CPUUtilization':
        AlarmName='ad_alerts_cpu_'+instance_id
        if count >=1:
            AlarmName = 'ad_alerts_disk'+str(count)+'_'+instance_id
        Dimensions = [[{
                    'Name': 'InstanceId',
                    'Value': instance_id
                }]]
    elif metric_name == "DiskSpaceUtilization" or metric_name == "LogicalDisk % Free Space":
        AlarmName = 'ad_alerts_disk_'+instance_id
        static_alarms = get_static_alarms()
        if static_alarms:
            print('static alarms are present ',static_alarms)
            Dimensions= get_alarms(static_alarms,instance_id)
        else:
            print('No static alarms to this instance')
    client = boto3.client('cloudwatch', config=config)
    count = 0
    for Dimension in Dimensions:
        print("start creating anomaly alarms")
        if count > 0:
            AlarmName = 'ad_alerts_disk'+str(count)+'_'+instance_id
        print('Dimension is ',Dimension)
        error_status = False
        try:
            client.put_metric_alarm(
                AlarmName = AlarmName,
                AlarmDescription="this is dynamic alarm",
                ActionsEnabled=True,
                AlarmActions=[
                    alarm_action],
                EvaluationPeriods=evalution_period,
                DatapointsToAlarm=datappoints,
                ComparisonOperator='GreaterThanUpperThreshold',
                TreatMissingData='missing',
                Metrics=[{
                    'Id': 'm1',
                    'MetricStat': {
                        'Metric': {
                            'Namespace': namespace,
                            'MetricName': metric_name,
                            'Dimensions': Dimension
                        },
                        'Period': 300,
                        'Stat': 'Maximum'
                    },
                    'ReturnData': True
                }, {
                    'Id': 'ad1',
                    'Expression': expression,
                    'ReturnData': True
                }],
                ThresholdMetricId='ad1'
            )
        except Exception as e:
            error_status = True
            AlarmName = ""
            print("Error while creating_anomaly_alarm() for this instance id  - ",instance_id," ",e)
        if not error_status:
            anomaly_report(AlarmName,instance_id,metric_name,writer,customer,account_id)
            count =count +1 

    return AlarmName

def instance(instance_id,evalution_period,datappoints,alarm_action,expression,metric_name,writer,customer,account_id):
    try:
        platform = platform_checker(instance_id)
        if metric_name == "MemoryUtilization" or metric_name == "Memory % Committed Bytes In Use":
            if platform == 'windows':
                metric_name = "Memory % Committed Bytes In Use"
                namespace = "Windows/Default"
            else:
                metric_name = 'MemoryUtilization'
                namespace = "CWAgent"
        elif metric_name == "CPUUtilization":
            metric_name = "CPUUtilization"
            namespace = "AWS/EC2"
        elif metric_name == "DiskSpaceUtilization" or metric_name == "LogicalDisk % Free Space":
            if platform == 'windows':
                metric_name = "LogicalDisk % Free Space"
                namespace = "Windows/Default"
            else:
                metric_name = 'DiskSpaceUtilization'
                namespace = "CWAgent"
        
        alarm_name = create_anomaly_alarm(instance_id,evalution_period,datappoints,alarm_action,expression,metric_name,namespace,writer,customer,account_id)
    except Exception as e:
        alarm_name = ''
        print("Error in instance() - ",e)
    return alarm_name

def platform_checker(instance_id):
    
    print("platform_checker called")
    ec2 = boto3.resource('ec2', config=config)
    try:
        instance = ec2.Instance(instance_id)
        platform = instance.platform
    except Exception as e:
        platform=""
        print("Error in instance() - ",e)
    return platform

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
        print('get_data response is ',response)
    except Exception as e:
        response = ''
        print("Error get_data() - ",e)
    return response
    
def check_metric(name):
    names = name.split('-')
    # print(name.split('-'))
    metric_names=[]
    for tag in names:
        if tag == 'mem':
            print("this is memory tag",tag)
            metric_names.append('MemoryUtilization')
        elif tag == 'disk':
            print('this is disk tag',tag)
            metric_names.append('DiskSpaceUtilization')
        else:
            print('Invalid tag',tag)
    return metric_names

def lambda_handler(event, context):
  
    try:
        str1 = ''
        writer = ''
        anomaly_alarms = []
        str1= str1.join(event['resources'])
        instance_id = str1.split('/')[1]
        print('instance_id',instance_id)
        tags = event['detail']['tags']
        event= {}
        keys_list = tags.keys()
        if 'adalarm' in keys_list:
            tag_name = tags['adalarm']
            metric_names = check_metric(tag_name)
            csvio = io.StringIO()
            writer = csv.writer(csvio)
            writer.writerow([
                'Customer Name',
                'Account ID',
                'Region',
                'Instance ID',
                'Anomaly Detection Alarm',
                'Metric Name',
                'Created Date'
            ])
            # timestr = time.strftime("%Y-%m-%d-%H-%M-%S")
            now = datetime.now()
            timestr = now.strftime("%Y-%m-%d-%H-%M-%S.%f")
            file_name ='feature-cw-anomaly-detection/alarms_report/enabled_anomaly_alarms/enabled_anomay_alarms_report_' + timestr + '.csv'
            for metric in metric_names:
                print('metric is ',metric)
                response = get_data(metric)
                datappoints = int(response['Item']['Data Points'])
                evalution_period = int(response['Item']['Evalution Period'])
                metric_name = response['Item']['Metric Name']
                alarm_action = response['Item']['SNS Topic ARN']
                expression = 'ANOMALY_DETECTION_BAND(m1, 2)'
                bucket = response['Item']['S3 Bucket']
                customer = ssm_parameter(customer_name)
                account_id = boto3.client("sts").get_caller_identity()["Account"]
                s3_bucket = boto3.client('s3', config=config)
                bucket = bucket
                anomaly_alarm = instance(instance_id,evalution_period,datappoints,alarm_action,expression,metric_name,writer,customer,account_id)
                anomaly_alarms.append(anomaly_alarm)
            if metric_names:
                s3_bucket.put_object(Body=csvio.getvalue(), ContentType='application/vnd.ms-excel', Bucket=bucket, Key=file_name) 
                csvio.close()
            print("anomaly alarms are : ",anomaly_alarms)
            print("instance id ",instance_id)
            event["instance_id"]=instance_id
            event["anomaly_alarm"]=anomaly_alarms
        else:
            print("we don't have any instance with given tag")         
    except Exception as e:
        print("Error lambda_handler() - ",e)

    return event