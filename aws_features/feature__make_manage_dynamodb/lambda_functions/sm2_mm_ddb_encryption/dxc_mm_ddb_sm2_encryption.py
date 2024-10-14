'''
    This Lambda function is used to encrypt the DynamoDB table based on tags we add in the table.
    Lambda is part of MakeManageDynamoDB step function.
    
    Conditions on which table will get encrypted by either by kms-id or remain as default with "Managed by DynamoDB" 

    1) If Encryption - False  ==> Table will not get encrypted by any kms-id, rather will be encrypted bydefault with "Managed by DynamoDB"
    2) If Encryption - True   ==> Table is encrypted using default kms-id (aws-managed)
    3) If Encryption - True and optional "kms" tag is provided  ==> Table is encrypted with custom cmk provided in the table tags. for ex - kms :  <custom-cmk-value> in dynamodb table. 
    4) If Encryption value is not provided  ==> Nothing will happen and Table is encrypted bydefault with "Managed by DynamoDB"
    
    Input event of the lambda function is
        {
            'TableName': '<TableName>', 
            'TableArn': '<TableARN>', 
            'TaskToken': '<Dynamically generated TaskToken>',
            'ParameterSetName': ''
        }
    
    On SUCCESSFUL check, DynamoDB table is encrypted by either default kms-id (aws-managed) or by custom cmk when we provide optional tag 'kms' with 'kms-id'
    as a value in the DynamoDB table with mandatory tag 'encryption' as 'true'.
    
    On FAILURE, DynamoDB table is not encrypted with any kms_id (either default or custom cmk) rather encryption will be "Managed by DynamoDB"
    
    Author : Rachit Mishra
    CreationDate : 24 Feb 2023
    ModifiedDate : 19 May 2023

'''
from botocore.config import Config
import os
import json
from boto_helper import boto_helper
boto_obj = boto_helper()

ddb_param_set_table = os.environ['MMDdbParamSetTableName']
ddb_rep_table = os.environ['MMDdbRepTableName']
dynamodb_log_group=os.environ['MMDdbLogGroupName']
dynamodb_log_stream=os.environ['MMDdbLogStreamName']


def lambda_handler(event, context):
    # TODO implement
    print('Event Received :', event)

    taskToken = event['TaskToken']
    tableName = event['TableName']
    tableArn = event['TableArn']    
    parameterSetName = event['ParameterSetName']
    stateName = 'DynamodbEncryption'
    error = {}
    error['TableArn'] = tableArn

    try:
        param_set_encryption_check = boto_obj.get_param_set_encryption_item(parameterSetName,ddb_param_set_table)
        print("param_set_encryption_check - ", param_set_encryption_check)

        Encryption_tag = param_set_encryption_check['Item']['Encryption']
        KMS_tag_key_id = param_set_encryption_check['Item']['KMS']

        if Encryption_tag:
            bool_encryption = boto_obj.str_to_bool(Encryption_tag)
            print("Boolean_encryption -", bool_encryption)

            if bool_encryption == True:
                if KMS_tag_key_id.lower() == 'default':
                    print("######## Encryption process has been started ########")
                    update_with_default_kms_id = boto_obj.update_table_encryption(tableName, bool_encryption)
                    print("######## Encryption process has been completed ########")
                    if 'success' in update_with_default_kms_id:
                        payload_json = {'TableName': tableName, 'TableArn': tableArn, 'TaskToken': taskToken, 'StateMachine': stateName, 'Message': 'Encrypted the table with the default kms id', 'ParameterSetName': parameterSetName}
                        print("Encrypted the table with the default kms id.Sending success task status")
                        boto_obj.handle_success(ddb_rep_table, tableName, stateName, 'Encrypted the table with the default kms id', taskToken, payload_json, parameterSetName)
                        boto_obj.put_log(dynamodb_log_group, dynamodb_log_stream, 'Encrypted the {} with the default kms id'.format(tableName))
                        boto_obj.put_log(dynamodb_log_group, tableName, 'Encrypted the {} with the default kms id'.format(tableName))                    
                    else:
                        error['Error'] = 'Exception occured while performing Encryption Tagging with default kms_id'
                        error['Cause'] = 'The update table encryption with default kms_id has been failed'
                        print("Exception occured while performing Encryption Tagging with default kms_id", error)
                        boto_obj.handle_failure(tableArn, ddb_rep_table, tableName, stateName, taskToken, error, parameterSetName)
                        boto_obj.put_log(dynamodb_log_group, dynamodb_log_stream, 'The update table encryption with default kms_id has been failed for the table {}'.format(tableName))
                        boto_obj.put_log(dynamodb_log_group, tableName, 'The update table encryption with default kms_id has been failed for the table {}'.format(tableName))                     
                
                else:
                    print("######## Encryption process has been started ########")
                    update_with_kms_id = boto_obj.update_table_encryption_with_kms_id(tableName, KMS_tag_key_id)
                    print("######## Encryption process has been completed ########")
                    if 'success' in update_with_kms_id:
                        payload_json = {'TableName': tableName, 'TableArn': tableArn, 'TaskToken': taskToken, 'StateMachine': stateName, 'Message': 'Encrypted the table with the user provided kms id', 'ParameterSetName': parameterSetName}
                        print("Encrypted the table with the user provided kms id. Sending success task status")
                        boto_obj.handle_success(ddb_rep_table, tableName, stateName, 'Encrypted the table with the user provided kms id', taskToken, payload_json, parameterSetName)
                        boto_obj.put_log(dynamodb_log_group, dynamodb_log_stream, 'Encrypted the {} with the user provided kms id'.format(tableName))
                        boto_obj.put_log(dynamodb_log_group, tableName, 'Encrypted the {} with the user provided kms id'.format(tableName))
                    else:
                        error['Error'] = 'Exception occured while performing Encryption using kms_id'
                        error['Cause'] = 'The update table encryption with kms_id has been failed'
                        print("Exception occured while performing Encryption using kms_id", error)
                        boto_obj.handle_failure(tableArn, ddb_rep_table, tableName, stateName, taskToken, error, parameterSetName)
                        boto_obj.put_log(dynamodb_log_group, dynamodb_log_stream, 'The update table encryption with kms_id has been failed for the table {}'.format(tableName))
                        boto_obj.put_log(dynamodb_log_group, tableName, 'The update table encryption with kms_id has been failed for the table {}'.format(tableName))

            else:
                check_encryption_response = boto_obj.check_table_encryption(tableName)
                if 'SSEDescription' in check_encryption_response['Table']:
                    print("######## Encryption process has been started ########")
                    response_for_default_kms_id = boto_obj.update_table_encryption(tableName, bool_encryption)
                    print("######## Encryption process has been completed ########")
                    if 'success' in response_for_default_kms_id:
                        payload_json = {'TableName': tableName, 'TableArn': tableArn, 'TaskToken': taskToken, 'StateMachine': stateName, 'Message': 'Table encryption has been updated and it is now Managed by DynamoDB', 'ParameterSetName': parameterSetName}
                        print("Table encryption has been updated and it is now Managed by DynamoDB.Sending success task status")
                        boto_obj.handle_success(ddb_rep_table, tableName, stateName, 'Table encryption has been updated and it is now Managed by DynamoDB', taskToken, payload_json, parameterSetName)
                        boto_obj.put_log(dynamodb_log_group, dynamodb_log_stream, '{} encryption has been updated and it is now Managed by DynamoDB'.format(tableName))
                        boto_obj.put_log(dynamodb_log_group, tableName, '{} encryption has been updated and it is now Managed by DynamoDB'.format(tableName))                         
                    else:
                        error['Error'] = 'Exception occured while performing Encryption'
                        error['Cause'] = 'The update table encryption with has been failed'
                        print("Exception occured while performing Encryption", error)
                        boto_obj.handle_failure(tableArn, ddb_rep_table, tableName, stateName, taskToken, error, parameterSetName)
                        boto_obj.put_log(dynamodb_log_group, dynamodb_log_stream, 'The update table encryption with has been failed for the table {}'.format(tableName))
                        boto_obj.put_log(dynamodb_log_group, tableName, 'The update table encryption with has been failed for the table {}'.format(tableName)) 
                else:
                    payload_json = {'TableName': tableName, 'TableArn': tableArn, 'TaskToken': taskToken, 'StateMachine': stateName, 'Message': 'Table is already encrypted by default - Managed by DynamoDB', 'ParameterSetName': parameterSetName}
                    print("Table is already encrypted by default - Managed by DynamoDB.Sending success task status")
                    boto_obj.handle_success(ddb_rep_table, tableName, stateName, 'Table is already encrypted by default - Managed by DynamoDB', taskToken, payload_json, parameterSetName)
                    boto_obj.put_log(dynamodb_log_group, dynamodb_log_stream, '{} is already encrypted by default - Managed by DynamoDB'.format(tableName))
                    boto_obj.put_log(dynamodb_log_group, tableName, '{} is already encrypted by default - Managed by DynamoDB'.format(tableName))   

        else:
            print("The Encryption tag value is BLANK. Hence,encryption is skipped. Sending success task status")
            payload_json = {'TableName': tableName, 'TableArn': tableArn, 'TaskToken': taskToken, 'StateMachine': stateName, 'Message': 'The Encryption tag value is BLANK. Hence,encryption is skipped', 'ParameterSetName': parameterSetName}
            boto_obj.handle_success(ddb_rep_table, tableName, stateName, 'The Encryption tag value is BLANK. Hence,encryption is skipped', taskToken, payload_json, parameterSetName)
            boto_obj.put_log(dynamodb_log_group, dynamodb_log_stream, 'The Encryption tag value is BLANK. Hence,encryption is skipped for the table {}'.format(tableName))
            boto_obj.put_log(dynamodb_log_group, tableName, 'The Encryption tag value is BLANK. Hence,encryption is skipped for the table {}'.format(tableName))            

    except Exception as e:
        print("'Exception occured while performing encryption-", e)
        error['Error'] = 'Exception occured while performing encryption'
        error['Cause'] = 'Encryption has been failed'
        boto_obj.handle_failure(tableArn, ddb_rep_table, tableName, stateName, taskToken, error, parameterSetName)
        boto_obj.put_log(dynamodb_log_group, dynamodb_log_stream, 'Exception occured while performing encryption for the table {}'.format(tableName))
        boto_obj.put_log(dynamodb_log_group, tableName, 'Exception occured while performing encryption for the table {}'.format(tableName))  
        raise