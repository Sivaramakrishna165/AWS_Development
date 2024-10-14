import json, os
from dynamodb_json import json_util as ddb_json
from boto_helper import boto_helper

import boto3
from botocore.config import Config

boto_obj = boto_helper()
const_def_val = ['/','','<DND. To Be Filled Automatically>']
ddb_param_set_tbl = os.environ['ddbParamSetTableName']
ddb_inst_info_tbl =  os.environ['ddbInstInfoTableName']
alarm_topic = os.environ['DXCInstanceAlarmTopic']

def chk_if_alarm_upt_required(existing, new):
    try:
        bln_result = False
        str_keys_to_compare = ['ComparisonOperator','Dimensions', 'Unit', 'Namespace',
                            'AlarmActions', 'ActionsEnabled', 'AlarmDescription', 'Statistic']
        int_keys_to_compare = ['Period', 'EvaluationPeriods','Threshold']
        for key in int_keys_to_compare:
            if(key not in existing):
                continue
            if(key == 'Threshold' and 'ThresholdOrBand' in new):
                if(int(existing[key]) != int(new['ThresholdOrBand'])):
                    print('There is a difference in metric - "{}" old-value "{}" required-value "{}"'.format(key, existing[key], new['ThresholdOrBand']))
                    bln_result = True
                continue
            if(int(existing[key]) != int(new[key])):
                print('There is a difference in metric - "{}" old-value "{}" required-value "{}"'.format(key, existing[key], new[key]))
                bln_result = True
        
        for key in str_keys_to_compare:
            if(key not in existing):
                continue
            if(key == 'Dimensions'):
                dimension_names = [obj['Name'] for obj in existing[key]]
                for name in dimension_names:
                    exiting_value = [obj['Name'] for obj in existing[key] if obj['Name'] == name]
                    new_value = [obj['Name'] for obj in new[key] if obj['Name'] == name]
                    if exiting_value != new_value:
                        print('There is a difference in Dimensions - "{}" old-value "{}" required-value "{}"'.format(name, exiting_value, new_value))
                        bln_result = True
                continue
            if(str(existing[key]) != str(new[key])):
                print('There is a difference in metric - "{}" old-value "{}" required-value "{}"'.format(key, existing[key], new[key]))
                bln_result = True
        return bln_result
    except Exception as e:
        print('Error compare_alarm_metrics() - ',e)
        raise e
    
    

def lambda_handler(event, context):

    try:
        print('Event - ', event)
        
        dynamo_item = ddb_json.loads(event['Records'][0])
        
        ddb_inst_info = os.environ['ddbInstInfoTableName']

        config = Config(retries=dict(max_attempts=10,mode='standard'))
        ddb_rsc = boto3.resource('dynamodb', config=config)

        event_type = dynamo_item['eventName']
        if(event_type.upper() == 'MODIFY' and 'Alarms' in dynamo_item['dynamodb']['NewImage']):
            instanceId = dynamo_item['dynamodb']['NewImage']['InstanceId']
            alarms = dynamo_item['dynamodb']['NewImage']['Alarms']
            inst_info_record = boto_obj.check_db_entry_exists(ddb_inst_info_tbl, 'InstanceId', instanceId)
            if(not inst_info_record):
                return "Record not available in DynamoDB table - {}".format(ddb_inst_info_tbl)
            
            parameter_set_name = inst_info_record['ParameterSetName']
            param_set_record = boto_obj.check_db_entry_exists(ddb_param_set_tbl, 'ParameterSetName', parameter_set_name)
            
            if(not param_set_record):
                return "Record not available in DynamoDB table - {}".format(ddb_param_set_tbl)
            
            if(param_set_record['ApplyMonitoring'].lower() == 'true'):
                print('ApplyMonitoring is set to true for instanceId: ', instanceId)

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
                volumes_index = 0
                if ('windows' in osname.lower()):
                    for alarm in alarms:
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
                            if('AlarmActions' in alarm and len(alarm['AlarmActions']) == 0):
                                alarm['AlarmActions'] = [alarm_topic]
                            
                            if('OKActions' in alarm and len(alarm['OKActions']) == 0):
                                alarm['OKActions'] = [alarm_topic]
                            if('Dimensions' in alarm):
                                for obj in alarm['Dimensions']:
                                    if obj['Name'] == 'InstanceId':
                                        obj['Value'] = instanceId
                            alarm['AlarmName'] = alarm_name
                            if(not bln_alarm_exists):
                                boto_obj.create_alarm(alarm, 'Create')
                            else:
                                print('Alarm - "{}" already available'.format(alarm_name))
                                available_alarm = boto_obj.get_alarm(alarm_name)
                                # print('available_alarm - ',available_alarm)
                                # print('new alarm - ', alarm)
                                if(chk_if_alarm_upt_required(available_alarm, alarm)):
                                    boto_obj.create_alarm(alarm, 'Update')
                                else:
                                    print('No updates required for Alarm - ',alarm_name)
                                    
                        except Exception as e:
                            print('ERROR while creating/updating alarm - {} ... error - {}'.format(alarm,str(e)))
                            continue
                else:
                    for alarm in alarms:
                        try:
                            # Constants for DiskSpaceUtilisation alarms
                            dimensions_keys = []
                            path_value = []
                            dimensions_values = []
                            alarm_name = 'MM_' + alarm['MetricName'] + '_' + instanceId + '_'+alarm['AlarmType']
                            if('Dimensions' in alarm):
                                if('AlarmActions' in alarm and len(alarm['AlarmActions']) == 0):
                                    alarm['AlarmActions'] = [alarm_topic]
                                
                                if('OKActions' in alarm and len(alarm['OKActions']) == 0):
                                    alarm['OKActions'] = [alarm_topic]
    
                                dimensions_keys = [obj['Name'] for obj in alarm['Dimensions']]
                                dimensions_values = [obj['Value'] for obj in alarm['Dimensions']]
                                path_value = [obj['Value'] for obj in alarm['Dimensions'] if obj['Name'] == 'path']
                                path_value = path_value[0] if len(path_value)==1 else None
                                
                                if(volumes_index >= len(volumes) and 'path' in dimensions_keys):
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
        
                                    # This is for additional volumes
                                    if obj['Name'] == 'path' and obj['Value'] in const_def_val:
                                        extDevice = volumes[volumes_index]['DeviceName']
                                        obj['Value'] = boto_obj.ssm_send_cmd(instanceId, extDevice, 'target')
                                    if obj['Name'] == 'device' and obj['Value'] in const_def_val:
                                        extDevice = volumes[volumes_index]['DeviceName']
                                        obj['Value'] = extDevice.split('/')[-1]
                                    if obj['Name'] == 'fstype' and obj['Value'] in const_def_val:
                                        extDevice = volumes[volumes_index]['DeviceName']
                                        obj['Value'] = boto_obj.ssm_send_cmd(instanceId, extDevice, 'fstype')    
                                        
                            alarm['AlarmName'] = alarm_name
                            bln_alarm_exists = boto_obj.chk_get_alarm_exists(alarm_name)
                            if(not bln_alarm_exists):
                                boto_obj.create_alarm(alarm)
                            else:
                                print('Alarm - "{}" already available'.format(alarm_name))
                                available_alarm = boto_obj.get_alarm(alarm_name)
                                # print('available_alarm - ',available_alarm)
                                # print('new alarm - ', alarm)
                                if(chk_if_alarm_upt_required(available_alarm, alarm)):
                                    boto_obj.create_alarm(alarm, 'Update')
                                else:
                                    print('No updates required for Alarm - ',alarm_name)
                        except Exception as e:
                            print('ERROR while creating/updating alarm - {} ... error - {}'.format(alarm,str(e)))
                            continue
                        finally:
                            if('path' in dimensions_keys and path_value in const_def_val):
                                volumes_index += 1
            else:
                return "ApplyMonitoring is set to False for insatnce - {} in dynamodbtable  - {}".format(instanceId, ddb_param_set_tbl)
        
            
        else:
            print('Doing Nothing. Not for Create item eventtype')
        
        return "Lambda executed Successfully"
    except Exception as e:
        print('Error lambda_handler() ', e)
        raise