'''
Boto Helper class contain all the supported aws api operations reauired for Create_Alarms to perform
'''

import boto3, json, time
from botocore.config import Config
from boto3.dynamodb.conditions import Attr
from datetime import datetime

class UpdateItemException(Exception):
    pass

class boto_helper():
    def __init__(self):
        config = Config(retries=dict(max_attempts=10,mode='standard'))
        self.cf_client = boto3.client('cloudformation', config=config)
        self.ec2_resource = boto3.resource('ec2', config=config)
        self.ec2_client = boto3.client('ec2', config=config)
        self.s3_client = boto3.client('s3', config=config)
        self.ssm_client = boto3.client('ssm', config=config)
        self.sg_client = boto3.client('stepfunctions',config=config)
        self.ddb = boto3.resource('dynamodb', config=config)
        self.cw_client = boto3.client('cloudwatch',config=config)
        self.supported_vol_types = {
                    'standard':'Magnetic',
                    'gp2': 'General.Purpose.SSD-gp2',
                    'gp3': 'General.Purpose.SSD-gp3',    
                    'io1':'Provisioned.IOPS.SSD',
                    'st1':'Throughput.Optimized.HDD',
                    'sc1':'Cold.HDD',
                    'None':None
                }
    def check_db_entry_exists(self, tbl_name, item_name, item_value):
        result = False
        try:
            table = self.ddb.Table(tbl_name)
            get_item_response = table.get_item(Key={item_name: item_value})
            if('Item' not in get_item_response):
                raise Exception('{} not vailable in ddbtable - {}'.format(item_value, tbl_name))
            if get_item_response['Item'][item_name] == item_value:
                return get_item_response['Item']
            else:
                print('Item %s not found' % item_name)
                return None
        except Exception as e:
            print("Error check_db_entry_exists() - {}".format(e))
            return False
            
        
    # Send task success to step function
    def send_task_success(self, taskToken, payload_json):
        try:
            response = self.sg_client.send_task_success(
                taskToken=taskToken,
                output = json.dumps(payload_json)
            )
            print('Task SUCCESS token sent - ',response)
    
        except Exception as e:
            print('Error send_task_success()-',e)
            raise
    
    # Send task failure to step function
    def send_task_failure(self, taskToken, error, cause):
        try:
            response = self.sg_client.send_task_failure(
                taskToken=taskToken,
                error = error,
                cause = cause
            )
            print('Task FAILURE token sent - ',response)
    
        except Exception as e:
            print('Error send_task_success()-',e)

    # Get the Volume type for the given InstanceId
    def get_volume_type(self, vol_id):
        try:
            for volume in self.ec2_resource.volumes.filter(
                VolumeIds=[vol_id
                ],
            ):
                if (volume.volume_type not in ['',None]):
                    return self.supported_vol_types[volume.volume_type]
                return None
        except Exception as e:
            print('Error get_volume_type()-',e)
            raise

    
        
    # Executes the send cmd for the instance for getting the df -h
    def ssm_send_cmd(self, instance_id, device, output_option):
        try:
            status = ''
            output_content = ''
            send_cmd_attempt = 0
            cmd = 'df -h {} --output={}'.format(device, output_option)
            print('cmd - ',cmd)
            send_cmd_attempt = 0
            while True:
                send_cmd_attempt += 1
                try:
                    response = self.ssm_client.send_command(InstanceIds=[instance_id],
                                DocumentName="AWS-RunShellScript",
                                Parameters={'commands': [cmd]})
                    command_id = response['Command']['CommandId']
                    attempt = 0
                    waiter = self.ssm_client.get_waiter('command_executed')
                    waiter.wait(
                            CommandId=command_id,
                            InstanceId=instance_id,
                            WaiterConfig={
                                'Delay': 1,
                                'MaxAttempts': 10
                            }
                        )
                    output = self.ssm_client.get_command_invocation(
                        CommandId=command_id,
                        InstanceId=instance_id)
                    output_content = output['StandardOutputContent']
                    #print(output_content)
                    output_content = output_content.lower().replace(' ','')
                    output_content = output_content.replace('\n','').replace('filesystem','').replace('type','').replace('mountedon','')
                    return output_content
                except Exception as e:
                    print('Error ssm_send_cmd() -',e)
                    pass
                if(send_cmd_attempt>5):
                    output = self.ssm_client.get_command_invocation(
                        CommandId=command_id,
                        InstanceId=instance_id)
                    #print('output',output)
                    if(output['Status'] != 'Success'):
                        raise Exception(output['StandardErrorContent'])
                    raise Exception('Failed, ssm is not installed or instance is in stopped state')
                else:
                    time.sleep(1) 
        except Exception as e:
            print('Error ssm_send_cmd() ',str(e))
            raise

        # Gets the all the volumes attached to the Instance
    def get_instance_volumes(self, instance_id):    
        try:
            response = self.ec2_client.describe_instances(InstanceIds=[instance_id])
            if(len(response['Reservations'])):
                return response['Reservations'][0]['Instances'][0]['BlockDeviceMappings']
            else:
                raise Exception('Instance/Volumes does not exist')
        except Exception as e:
            print('Error ',e)
            raise
    
    # Gets the Instance Type for the given InstanceID
    def get_instance_type(self, instance_id):    
        try:
            instance = self.ec2_resource.Instance(instance_id)
            return instance.instance_type
        except Exception as e:
            print('Error ',e)
            raise
    
    # Check if any alarm exists
    def chk_get_alarm_exists(self, alarm_name):
        try:
            response = self.cw_client.describe_alarms(
                AlarmNames=[alarm_name])
            return True if(len(response['MetricAlarms'])) else False
        except Exception as e:
            print('Erro chk_get_alarm_exists()-',e)
            raise e
            
    # Get alarm m
    def get_alarm(self, alarm_name):
        try:
            response = self.cw_client.describe_alarms(
                AlarmNames=[alarm_name])
            return response['MetricAlarms'][0] if(len(response['MetricAlarms'])) else False
        except Exception as e:
            print('Erro chk_get_alarm_exists()-',e)
            raise e

    # Include the below code for AWSPE-6479 Disk Alarms are not creating for instances having additional volumes - Amazon Linux 2 x86 and Arm
    # Executes the send cmd for the instance for getting the device name from OS level
    def ssm_send_cmd_device_name(self, osname, instance_id):
        try:
            status = ''
            output_content = ''
            send_cmd_attempt = 0
            if osname == 'ubuntu': 
                cmdlsblk = 'lsblk -o name -n -d -p -e7 | sort -k1'
            else: 
                cmdlsblk = 'lsblk -o name -n -d -p | sort -k1' 
            print('cmdblk', cmdlsblk)
            send_cmd_attempt = 0
            while True:
                send_cmd_attempt += 1
                try:
                    responselsblk = self.ssm_client.send_command(InstanceIds=[instance_id],
                                DocumentName="AWS-RunShellScript",
                                Parameters={'commands': [cmdlsblk]})

                    command_id = responselsblk['Command']['CommandId']
                    attempt = 0
                    waiter = self.ssm_client.get_waiter('command_executed')
                    waiter.wait(
                            CommandId=command_id,
                            InstanceId=instance_id,
                            WaiterConfig={
                                'Delay': 1,
                                'MaxAttempts': 10
                            }
                        )
                    output = self.ssm_client.get_command_invocation(
                        CommandId=command_id,
                        InstanceId=instance_id)
                    output_content = output['StandardOutputContent']
                    output_content = output_content.replace('\n',',')
                    return output_content
                except Exception as e:
                    print('Error ssm_send_cmd_device_name () -',e)
                    pass
                if(send_cmd_attempt>5):
                    output = self.ssm_client.get_command_invocation(
                        CommandId=command_id,
                        InstanceId=instance_id)
                    if(output['Status'] != 'Success'):
                        raise Exception(output['StandardErrorContent'])
                    raise Exception('Failed, ssm is not installed or instance is in stopped state')
                else:
                    time.sleep(1) 
        except Exception as e:
            print('Error ssm_send_cmd_device_name() ',str(e))
            raise
    
    # Gets the all the volumes attached to the Instance
    def get_instance_volumes(self, instance_id):    
        try:
            response = self.ec2_client.describe_instances(InstanceIds=[instance_id])
            if(len(response['Reservations'])):
                return response['Reservations'][0]['Instances'][0]['BlockDeviceMappings']
            else:
                raise Exception('Instance/Volumes does not exist')
        except Exception as e:
            print('Error ',e)
            raise
           
       # Get the Volume type for the given InstanceId
    def get_volume_type(self, vol_id):
        try:
            for volume in self.ec2_resource.volumes.filter(
                VolumeIds=[vol_id
                ],
            ):
                if (volume.volume_type not in ['',None]):
                    return self.supported_vol_types[volume.volume_type]
                return None
        except Exception as e:
            print('Error get_volume_type()-',e)
            raise
    
    # Create an alarm
    def create_alarm(self, metrics, mode='Create'):
        try:
            input_metrics = {}
            if('AlarmName' in metrics): input_metrics['AlarmName'] = metrics['AlarmName']
            if('AlarmActions' in metrics): input_metrics['AlarmActions'] = metrics['AlarmActions']
            if('AlarmDescription' in metrics): input_metrics['AlarmDescription'] = metrics['AlarmDescription']
            if('ComparisonOperator' in metrics): input_metrics['ComparisonOperator'] = metrics['ComparisonOperator']
            if('Dimensions' in metrics): input_metrics['Dimensions'] = metrics['Dimensions']
            if('MetricName' in metrics): input_metrics['MetricName'] = metrics['MetricName']
            if('Namespace' in metrics): input_metrics['Namespace'] = metrics['Namespace']
            if('Statistic' in metrics): input_metrics['Statistic'] = metrics['Statistic']
            if('ThresholdOrBand' in metrics): input_metrics['Threshold'] = int(metrics['ThresholdOrBand'])
            if('Threshold' in metrics): input_metrics['Threshold'] = int(metrics['Threshold'])
            if('Unit' in metrics): input_metrics['Unit'] = metrics['Unit']
            if('EvaluationPeriods' in metrics): input_metrics['EvaluationPeriods'] = int(metrics['EvaluationPeriods'])
            if('Period' in metrics): input_metrics['Period'] = int(metrics['Period'])
            print(input_metrics)
            self.cw_client.put_metric_alarm(**input_metrics)
            print('Alarm - "{}" {}ed successfully'.format(input_metrics['AlarmName'], mode))
        except Exception as e:
            print('Erro chk_get_alarm_exists()-',e)
            raise e
    
    
    # Update records to table
    def update_report_table(self, tbl_name, instance_id, status, state_detail):
        try:
            table = self.ddb.Table(tbl_name)
            currentDT = datetime.now()
            date_time = currentDT.strftime('%m-%d-%Y_%H%M%S')
            
            table.update_item(
                Key={
                    'InstanceId': instance_id
                },
                UpdateExpression='SET ModifyTime=:time, StateName=:state, StateSuccessFail=:status, StateDetail=:detail',
                ExpressionAttributeValues={
                    ':time': date_time,
                    ':state': 'CreateAlarms',
                    ':status': status,
                    ':detail': state_detail
                }
            )
            print('DDB Table - {} updated successfully for insatnceId - {}'.format(tbl_name, instance_id))
        except boto3.exceptions.botocore.client.ClientError as e:
            print("Error updating item: %s" % e)
            raise UpdateItemException("Error: %s" % e)

    # Update the Tag
    def update_tag(self, resource, key, value):
        try:
            update_tag_response = self.ec2_client.create_tags(
                Resources=[
                    resource,
                ],
                Tags=[
                    {
                        'Key': key,
                        'Value': value
                    },
                ]
            )
            print('Tag - "{}:{}" updated on resource - {}'.format(key, value, resource))
        except Exception as e:
            print("Error in update_tag", e)