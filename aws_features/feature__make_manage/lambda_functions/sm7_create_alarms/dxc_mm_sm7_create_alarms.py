'''
The Lambda funtion will create the CW Alarms for the InstanceId.
Required metrics for the alarms will fetched from dynamoDB table - FtMakeManageInstancesAlarms

Sample Request event:
        {
          "InstanceId": "<instanceId>",
          "ParameterSetName":"default",
          "TaskToken": "<stepfuntion-tasktoken>"
        }
'''

import json, os
from boto_helper import boto_helper
import boto3
from botocore.config import Config

ddb_inst_alarms_tbl = os.environ['ddbInstAlarmsTableName']
ddb_param_set_tbl = os.environ['ddbParamSetTableName']
ddb_report_tbl = os.environ['ddbInstRepTableName']
alarm_topic = os.environ['DXCInstanceAlarmTopic']
boto_obj = boto_helper()
const_def_val = ['','<DND. To Be Filled Automatically>']


def lambda_handler(event, context):

    try:
        print('Event - ', event)
        taskToken = event['TaskToken']
        instanceId = event['InstanceId']
        param_set_name = event['ParameterSetName']
        error = {}
        error['InstanceId'] = instanceId

        ddb_inst_info = os.environ['ddbInstInfoTableName']

        config = Config(retries=dict(max_attempts=10,mode='standard'))
        ddb_rsc = boto3.resource('dynamodb', config=config)
        
        param_set_record = boto_obj.check_db_entry_exists(ddb_param_set_tbl, 'ParameterSetName', param_set_name)
        if(param_set_record == None):
            print('ParameterSetName - {} is not available in DynamoDB table - {}'.format(param_set_name, ddb_param_set_tbl))
            return "Not valid"  # TO be Implemented Send Fail response or abort execution
        
        if(param_set_record['ApplyMonitoring'].lower() == 'true'):
            print('ApplyMonitoring is set to true for instanceId: ', instanceId)
            default_alarms = boto_obj.check_db_entry_exists(ddb_inst_alarms_tbl, 'InstanceId', instanceId)
        
            if(default_alarms):
                ddb_inst_info_table_obj = ddb_rsc.Table(ddb_inst_info)
                response = ddb_inst_info_table_obj.get_item(Key={
                            'InstanceId': instanceId
                        })
                instance_data = response['Item']
                print(instance_data)

                osname = instance_data['os-name'].strip()            
                osarch = instance_data['os-arch'].strip()
                print('osname is: {} and osarch is: {}'.format(osname,osarch))

                volumes = boto_obj.get_instance_volumes(instanceId)
                print(volumes)
                print(type(volumes))
                volumes_index = 1
                if ('windows' in osname.lower()):
                    for alarm in default_alarms['Alarms']:
                        try:
                            drive = [obj['Value'] for obj in alarm['Dimensions'] if obj['Name'] == 'instance']
                            if(len(drive)==1): 
                                alarm_name = 'MM_' + alarm['MetricName'] + '_' + instanceId + '_'+ drive[0] + '_' + alarm['AlarmType']
                                if(alarm['MetricName'] == 'LogicalDisk % Free Space'):
                                    if(len(volumes) < 2 and drive == ['D:']):
                                        continue
                                    if(len(volumes) < 3 and drive == ['E:']):
                                        continue
                            else:
                                alarm_name = 'MM_' + alarm['MetricName'] + '_' + instanceId + '_'+alarm['AlarmType']
                            bln_alarm_exists = boto_obj.chk_get_alarm_exists(alarm_name)
                            if(not bln_alarm_exists):
                                if('AlarmActions' in alarm and len(alarm['AlarmActions']) == 0):
                                    alarm['AlarmActions'] = [alarm_topic]
                                
                                if('OKActions' in alarm and len(alarm['OKActions']) == 0):
                                    alarm['OKActions'] = [alarm_topic]
                                if('Dimensions' in alarm):
                                    for obj in alarm['Dimensions']:
                                        if obj['Name'] == 'InstanceId':
                                            obj['Value'] = instanceId
                                alarm['AlarmName'] = alarm_name
                                boto_obj.create_alarm(alarm)
                            else:
                                print('Alarm - "{}" already available'.format(alarm_name))
                        except Exception as e:
                            print('ERROR while creating alarm - {} ... error - {}'.format(alarm,str(e)))
                            continue
                else:
                    # Logic for creating Linux Alarms
                    for alarm in default_alarms['Alarms']:
                        try:
                            # Constants for DiskSpaceUtilisation alarms
                            dimensions_keys = []
                            path_value = []
                            dimensions_values = []
                            alarm_name = 'MM_' + alarm['MetricName'] + '_' + instanceId + '_'+alarm['AlarmType']
                            if('Dimensions' in alarm):
                                dimensions_keys = [obj['Name'] for obj in alarm['Dimensions']]
                                dimensions_values = [obj['Value'] for obj in alarm['Dimensions']]
                                path_value = [obj['Value'] for obj in alarm['Dimensions'] if obj['Name'] == 'path']
                                path_value = path_value[0] if len(path_value)==1 else None
                                
                                if(volumes_index >= len(volumes) and 'path' in dimensions_keys and '/' not in dimensions_values):
                                    print('Ignoring the DiskSpaceUtilisation Alarm - "{}" creation. No. of Volumes are NOT matching with the DiskSpaceUtilisation alarms'.format(alarm))
                                    continue
                                if('path' in dimensions_keys and '/' in dimensions_values):
                                    alarm['AlarmDescription'] = alarm['AlarmDescription'] + ' '+volumes[0]['Ebs']['VolumeId']
                                    alarm_name = 'MM_' + alarm['MetricName'] + '_' + instanceId + '_'+volumes[0]['Ebs']['VolumeId']+'_'+alarm['AlarmType']
                                
                                # print(path_value)
                                if('path' in dimensions_keys and path_value in const_def_val):
                                    alarm['AlarmDescription'] = alarm['AlarmDescription'] + ' '+volumes[volumes_index]['Ebs']['VolumeId']
                                    alarm_name = 'MM_' + alarm['MetricName'] + '_' + instanceId + '_'+volumes[volumes_index]['Ebs']['VolumeId']+'_'+alarm['AlarmType']
                                    # volumes_index += 1
                           
                            bln_alarm_exists = boto_obj.chk_get_alarm_exists(alarm_name)
                            if(not bln_alarm_exists):
                                if('AlarmActions' in alarm and len(alarm['AlarmActions']) == 0):
                                    alarm['AlarmActions'] = [alarm_topic]
                                
                                if('OKActions' in alarm and len(alarm['OKActions']) == 0):
                                    alarm['OKActions'] = [alarm_topic]
    
                                if('Dimensions' in alarm):
                                    for obj in alarm['Dimensions']:
                                        
                                        if obj['Name'] == 'InstanceId' and obj['Value'] in const_def_val:
                                            obj['Value'] = instanceId
                                            
                                        # This is for root volume
                                        if obj['Name'] == 'device' and 'path' in dimensions_keys and '/' in dimensions_values:
                                            obj['Value'] = boto_obj.ssm_send_cmd(instanceId, '/root','source').split('/')[-1]
                                        if obj['Name'] == 'fstype' and 'path' in dimensions_keys and '/' in dimensions_values:
                                            obj['Value'] = boto_obj.ssm_send_cmd(instanceId,'/root','fstype')
                                        
                                        # Included the below code as part of AWSPE-6479 to get the device name form OS level
                                        volumeDeviceName = (boto_obj.ssm_send_cmd_device_name(osname.lower(), instanceId))
                                        volumeDeviceName = volumeDeviceName [:-1]
                                        OSVolumeDeviceName = volumeDeviceName.split(',')
                                        # End of AWSPE-6479
                                        
                                        # This is for additional volumes
                                        if obj['Name'] == 'path' and obj['Value'] in const_def_val:
                                        # Included the below code as part of AWSPE-6479 to get the device name form OS level
                                            #extDevice = volumes[volumes_index]['DeviceName']
                                            extDevice = OSVolumeDeviceName[volumes_index]
                                            obj['Value'] = boto_obj.ssm_send_cmd(instanceId, extDevice, 'target')
                                        if obj['Name'] == 'device' and obj['Value'] in const_def_val:
                                            #extDevice = volumes[volumes_index]['DeviceName']
                                        # Included the below code as part of AWSPE-6479 to get the device name form OS level
                                            extDevice = OSVolumeDeviceName[volumes_index]
                                            obj['Value'] = extDevice.split('/')[-1]
                                         
                                        if obj['Name'] == 'fstype' and obj['Value'] in const_def_val:
                                            #extDevice = volumes[volumes_index]['DeviceName']
                                        # Included the below code as part of AWSPE-6479 to get the device name form OS level
                                            extDevice = OSVolumeDeviceName[volumes_index]
                                            obj['Value'] = boto_obj.ssm_send_cmd(instanceId, extDevice, 'fstype')    
                                        
                                alarm['AlarmName'] = alarm_name
                                boto_obj.create_alarm(alarm)
                            else:
                                print('Alarm - "{}" already available'.format(alarm_name))
                            if('path' in dimensions_keys and path_value in const_def_val):
                                volumes_index += 1
                        except Exception as e:
                            print('ERROR while creating alarm - {} ... error - {}'.format(alarm,str(e)))
                            continue
            else:
                print('No default alarms exists')
                # TO be Implemented Send Fail response or abort execution

        else:
            print('ApplyMonitoring is set to false for instanceId: ', instanceId)
            # To be Implemented, Pass the send token to next State Machine
        
        boto_obj.update_report_table(ddb_report_tbl, instanceId, 'SUCCESS', 'Alarm created successfully')
        payload_json = {'InstanceId':instanceId, 'TaskToken':taskToken, 'ParameterSetName': event['ParameterSetName'],
                            'StateMachine':'CreateAlarms', 'Message':'CreateAlarms - Success'}
        boto_obj.send_task_success(taskToken, payload_json)
        return "Lambda executed Successfully"
    except Exception as e:
        error['Error'] = 'Instance Tagging Lambda exception Occurred'
        boto_obj.update_tag(instanceId, 'dxc_make_manage','Fail')
        boto_obj.update_report_table(ddb_report_tbl, instanceId, 'FAIL', str(e))
        boto_obj.send_task_failure(taskToken, json.dumps(error), str(e))
        print('Error lambda_handler() ', e)
        raise