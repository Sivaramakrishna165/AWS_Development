'''
aws_iam_access_analyzer.py will perform the following:
    - Upon Offering deployment, EnableFeature is True, feature__aws_iam_access_analyzer will be deployed and will create an AWS IAM Access Analyzer - external access analyzer
'''
import boto3
import json, datetime
import urllib3
import os
import logging
from botocore.exceptions import ClientError
from botocore.config import Config
import time
import ast
from time import sleep

logger = logging.getLogger()
logger.setLevel(logging.INFO)

config=Config(retries=dict(max_attempts=10,mode='standard'))
client = boto3.client('accessanalyzer')

ddb = boto3.resource('dynamodb', config=config)
ddb_client = boto3.client('dynamodb', config=config)

http = urllib3.PoolManager()
SUCCESS = "SUCCESS"
FAILED = "FAILED"

def send_response(event, context, responseStatus, responseData, physicalResourceId=None, noEcho=False, reason=None):
    try:
        responseUrl = event['ResponseURL']
        responseBody = {
            'Status' : responseStatus,
            'Reason' : "{}, See the details in CloudWatch Log Stream: {}".format(reason,context.log_stream_name),
            #'PhysicalResourceId' : context.log_stream_name,
            'PhysicalResourceId' : 'CustomResourcePhysicalID',
            'StackId' : event['StackId'],
            'RequestId' : event['RequestId'],
            'LogicalResourceId' : event['LogicalResourceId'],
            'NoEcho' : noEcho,
            'Data' : {'ReturnData':responseData}
        }

        json_responseBody = json.dumps(responseBody)

        print("Response body:")
        print(json_responseBody)

        headers = {
            'content-type' : '',
            'content-length' : str(len(json_responseBody))
        }
        try:
            response = http.request('PUT', responseUrl, headers=headers, body=json_responseBody)
            print("Status code:", response.status)

        except Exception as e:
            print("send(..) failed executing http.request(..):", e)
    except Exception as e:
        print('Error send_response() - ',e)
        raise


def create_analyzer_db_table():
    try:
        send_response_dict = {'responseStatus': 'FAILED', 'responseData': 'FAILED'}
        
        create_table_response = ddb_client.create_table(
            AttributeDefinitions=[
                {
                    'AttributeName': 'AccessAnalyzerName',
                    'AttributeType': 'S'
                }
            ],
            TableName='dxcms-iam-access-analyzer',
            KeySchema=[
                {
                    'AttributeName': 'AccessAnalyzerName',
                    'KeyType': 'HASH'
                }
            ],
            BillingMode='PAY_PER_REQUEST',
            Tags=[
                {
                    'Key': 'Owner',
                    'Value': 'DXC'
                }
            ]
        )
        send_response_dict['responseStatus'] = 'SUCCESS'
        send_response_dict['responseData'] = 'SUCCESS'
        sleep(10)
        return create_table_response, send_response_dict

    except Exception as e:
        print('An Error occurred in create_access_analyzer', e)
        send_response_dict['responseStatus'] = 'FAILED'
        send_response_dict['responseData'] = 'Error in create_access_analyzer - {}'.format(e)
        return 'FAILED', send_response_dict



def get_db_item(tbl_name, partition_key, partition_value, sort_key=None, sort_value=None):
    try:
        print("starting get_db_item")
        send_response_dict = {'responseStatus': 'FAILED', 'responseData': 'FAILED'}
        table = ddb.Table(tbl_name)
        if sort_key == None:
            get_item_response = table.get_item(Key={partition_key: partition_value})
        else:
            get_item_response = table.get_item(Key={partition_key: partition_value, sort_key: sort_value})
        print("get_item_response in get_db_item is ", get_item_response)
        send_response_dict['responseStatus'] = 'SUCCESS'
        send_response_dict['responseData'] = 'SUCCESS'
        return get_item_response, send_response_dict
    except ClientError as e:
        print("ClientError in get_db_item is: ", e)
        send_response_dict['responseStatus'] = 'FAILED'
        send_response_dict['responseData'] = 'Error in get_db_item- {}'.format(e)
        return 'FAILED', send_response_dict
    except Exception as e:
        print('An Error occurred in get_db_item ', e)
        send_response_dict['responseStatus'] = 'FAILED'
        send_response_dict['responseData'] = 'Error in get_db_item- {}'.format(e)
        return 'FAILED', send_response_dict

def get_ext_anal_rules(analyzer_name):
    try:
        send_response_dict = {'responseStatus': 'FAILED', 'responseData': 'FAILED'}
        print("getting external analyzer rules")
        nextToken = '' # Initialize in case MaxResults greater than 50 
        while(nextToken is not None):
            if nextToken is None or nextToken == '':
                list_archive_rules_response = client.list_archive_rules(
                    analyzerName=analyzer_name
                )
            else:
                list_archive_rules_response = client.list_archive_rules(
                    analyzerName=analyzer_name,
                    nextToken=nextToken,
                    maxResults=50
                )
            nextToken = list_archive_rules_response['nextToken'] if('nextToken' in list_archive_rules_response) else None
        print("list_archive_rules_response in get_ext_anal_rules is ", list_archive_rules_response)
        send_response_dict['responseStatus'] = 'SUCCESS'
        send_response_dict['responseData'] = 'SUCCESS'
        return list_archive_rules_response, send_response_dict

    except ClientError as e:
        print("ClientError in get_ext_anal_rules is: ", e)
        send_response_dict['responseStatus'] = 'FAILED'
        send_response_dict['responseData'] = 'Error in get_ext_anal_rules- {}'.format(e)
        return 'FAILED', send_response_dict
    except Exception as e:
        print('An Error occurred in get_ext_anal_rules', e)
        send_response_dict['responseStatus'] = 'FAILED'
        send_response_dict['responseData'] = 'Error in get_ext_anal_rules- {}'.format(e)
        return 'FAILED', send_response_dict


def add_items(tbl_name, obj_json):
    try:
        print("starting add_items")
        print("tbl_name in add_items is ", tbl_name)
        print("obj_json in add_items is ", obj_json)
        send_response_dict = {'responseStatus': 'FAILED', 'responseData': 'FAILED'}
        table = ddb.Table(tbl_name)
        print("table in add_items is type ", type(table))
        print(obj_json)
        put_item_response = table.put_item(Item=obj_json)
        print("put_item_response in add_items is ", put_item_response)
        send_response_dict['responseStatus'] = 'SUCCESS'
        send_response_dict['responseData'] = 'SUCCESS'
        sleep(2)
        return put_item_response, send_response_dict
    except ClientError as e:
        print("ClientError in add_items is: ", e)
        send_response_dict['responseStatus'] = 'FAILED'
        send_response_dict['responseData'] = 'Error in add_items- {}'.format(e)
        return 'FAILED', send_response_dict
    except Exception as e:
        print('An Error occurred in add_items', e)
        send_response_dict['responseStatus'] = 'FAILED'
        send_response_dict['responseData'] = 'Error in add_items- {}'.format(e)
        return 'FAILED', send_response_dict

def create_default_db_items(analyzer_name, tbl_name, function_name):
    ### Create defaults for feature aws_iam_access_analyzer, use generic name for 10.0 and 11.0 analyzer features
    send_response_dict = {'responseStatus': 'FAILED', 'responseData': 'FAILED'}
    # The AttributeValue for a key attribute cannot contain an empty string value 
    try:
        JsonRules = [
            {
                'ruleName': 'ArchiveRule-dxcms-federated',
                    "filter": {
                        "isPublic": {
                            "eq": [
                                "false"
                            ]
                        },
                        "principal.Federated": {
                            "contains": [
                                "dxciam-okta-awsc",
                                "dxc-cliam-adfs-use2p",
                                "dxciam-okta-awsec",
                                "dxc-cliam-adfs-iew1p"
                            ]
                        }
                    }
            },
            {
                'ruleName': 'ArchiveRule-dxcms-billing-migrator-role',
                    "filter": {
                        "isPublic": {
                            "eq": [
                                "false"
                            ]
                        },
                        "resource": {
                            "contains": [
                                "BillingConsolePolicyMigratorRole"
                            ]
                        }
                    }
            }

        ]
        tags={"Owner": "DXC", "Application": function_name}
 
        default_db_json = {
            "AccessAnalyzerName": analyzer_name, 
            "external-access-analyzer-archive-rule": JsonRules,
            "external-access-analyzer-tags": tags
        }
        print("default_db_json in create_default_db_items is ", default_db_json)
        print("type of default_db_json in create_default_db_items is ", type(default_db_json)) 
        print("tbl_name in create_default_db_items is ", tbl_name)
        add_items_response, send_response_dict = add_items(tbl_name, default_db_json)
        return add_items_response, send_response_dict
    except Exception as e:
        print('Error creating default item for external-access-analyzer-archive-rule in create_default_db_items', e)
        send_response_dict['responseStatus'] = 'FAILED'
        send_response_dict['responseData'] = 'Error creating default item for external-access-analyzer-archive-rule in create_default_db_items - {}'.format(e)
        return 'FAILED', send_response_dict


def get_ssm_parameter(name):
    ssm_client = boto3.client('ssm',config=config)
    get_parameter_response = ssm_client.get_parameter(
        Name=name
    )
    ssm_parameter = get_parameter_response['Parameter']
    ssm_parameter_value = ssm_parameter['Value']
    return ssm_parameter_value


def create_access_analyzer(analyzer_name, analyzer_type, archive_rule, function_name):
    try:
        send_response_dict = {'responseStatus': 'FAILED', 'responseData': 'FAILED'}
        print("archive_rule in create_access_analyzer is ", archive_rule)
        print("archive_rule type is ", type(archive_rule))
 
        # clientToken is autopopulated since not provided
        # need two separate create_analyzer sections, depending on value of archive_rules
        print("analyzer_name is ", analyzer_name)
        if archive_rule == 'Blank':
            print("creating analyzer without archive rules")
            create_analyzer_response = client.create_analyzer(
                analyzerName=analyzer_name,
                type=analyzer_type,
            )
        else:
            print("creating analyzer with archive rules")
            create_analyzer_response = client.create_analyzer(
                analyzerName=analyzer_name,
                archiveRules=archive_rule,
                type=analyzer_type,
                tags={"Owner": "DXC", "Application": function_name}
            )

        send_response_dict['responseStatus'] = 'SUCCESS'
        send_response_dict['responseData'] = 'SUCCESS'
        return create_analyzer_response, send_response_dict
    except Exception as e:
        print('An Error occurred in create_access_analyzer', e)
        send_response_dict['responseStatus'] = 'FAILED'
        send_response_dict['responseData'] = 'Error in create_access_analyzer - {}'.format(e)
        return 'FAILED', send_response_dict

def do_update_archive_rule(analyzer_name, rule_name, rule_filter):
    try:
        send_response_dict = {'responseStatus': 'FAILED', 'responseData': 'FAILED'}
        update_archive_rule_response = client.update_archive_rule(
            analyzerName=analyzer_name,
            ruleName=rule_name,
            filter=rule_filter
        )
        send_response_dict['responseStatus'] = 'SUCCESS'
        send_response_dict['responseData'] = 'SUCCESS'
        return send_response_dict

    except Exception as e:
        print('An Error occurred in do_update_archive_rule', e)
        send_response_dict['responseStatus'] = 'FAILED'
        send_response_dict['responseData'] = 'Error in do_update_archive_rule - {}'.format(e)
        return send_response_dict

def do_create_archive_rule(analyzer_name, rule_name, rule_filter):
    try:
        send_response_dict = {'responseStatus': 'FAILED', 'responseData': 'FAILED'}
        create_archive_rule_response = client.create_archive_rule(
            analyzerName=analyzer_name,
            ruleName=rule_name,
            filter=rule_filter
        )
        send_response_dict['responseStatus'] = 'SUCCESS'
        send_response_dict['responseData'] = 'SUCCESS'
        return send_response_dict

    except Exception as e:
        print('An Error occurred in do_create_archive_rule', e)
        send_response_dict['responseStatus'] = 'FAILED'
        send_response_dict['responseData'] = 'Error in do_create_archive_rule - {}'.format(e)
        return send_response_dict

def do_delete_archive_rule(analyzer_name, rule_name):
    try:
        send_response_dict = {'responseStatus': 'FAILED', 'responseData': 'FAILED'}
        delete_archive_rule_response = client.delete_archive_rule(
            analyzerName=analyzer_name,
            ruleName=rule_name
        )
        send_response_dict['responseStatus'] = 'SUCCESS'
        send_response_dict['responseData'] = 'SUCCESS'
        return send_response_dict

    except Exception as e:
        print('An Error occurred in do_delete_archive_rule', e)
        send_response_dict['responseStatus'] = 'FAILED'
        send_response_dict['responseData'] = 'Error in do_delete_archive_rule - {}'.format(e)
        return send_response_dict

def update_analyzer(get_db_item_response, get_ext_anal_rules_response, analyzer_name):
    try:
        send_response_dict = {'responseStatus': 'FAILED', 'responseData': 'FAILED'}

        ### create analyzer rule list
        current_analyzer_rule_list = []
        for anal_list_entry in get_ext_anal_rules_response['archiveRules']:
            for key, value in anal_list_entry.items():
                if key == 'ruleName':
                    current_analyzer_rule_list.append(value)
        print("current_analyzer_rule_list in update_analyzer is ", current_analyzer_rule_list)

        ### create DB rule name list
        current_db_rule_list = []
        for db_list_entry in get_db_item_response['Item']['external-access-analyzer-archive-rule']:
            for key, value in db_list_entry.items():
                if key == 'ruleName':
                    current_db_rule_list.append(value)
        print("current_db_rule_list is ", current_db_rule_list)

        ###  compare DB rule names to Analyzer rule names and perform update or add
        for db_list_entry in get_db_item_response['Item']['external-access-analyzer-archive-rule']:
            for key, value in db_list_entry.items():
                if key == 'ruleName':
                    if value in current_analyzer_rule_list:
                        # perform update 
                        print('performing update_archive_rule on {}'.format(value))
                        send_response_dict = do_update_archive_rule(analyzer_name, value, db_list_entry['filter'])
                        print("send_response_dict for do_update_archive_rule is ", send_response_dict)
                    else:
                        print('performing create_archive_rule on {}'.format(value))
                        send_response_dict = do_create_archive_rule(analyzer_name, value, db_list_entry['filter'])
                        print("send_response_dict for do_create_archive_rule is ", send_response_dict)

            # allow time to complete the update before processing deletes
            sleep(5)

        ### compare Analyzer rule name to DB rule names and perform delete
        for anal_rule in current_analyzer_rule_list:
            if anal_rule not in current_db_rule_list:
                print('deleting anal_rule {} from the analyzer'.format(anal_rule))
                send_response_dict = do_delete_archive_rule(analyzer_name, anal_rule)
                print("send_response_dict for do_delete_archive_rule is ", send_response_dict)

        return send_response_dict
    except Exception as e:
        print('An Error occurred in update_analyzer', e)
        send_response_dict['responseStatus'] = 'FAILED'
        send_response_dict['responseData'] = 'Error in update_analyzer - {}'.format(e)
        return send_response_dict

def update_analyzer_tags(tags_in_db, analyzer_name):
    try:
        send_response_dict = {'responseStatus': 'FAILED', 'responseData': 'FAILED'}

        get_analyzer_response = client.get_analyzer(
            analyzerName=analyzer_name
        )
        print("get_analyzer_response in update_analyzer_tags is ", get_analyzer_response)
        
        analyzer_arn = get_analyzer_response['analyzer']['arn']
        print("analyzer_arn is ", analyzer_arn)

        print("applying tags from DB to analyzer")
        tag_resource_response = client.tag_resource(
            resourceArn=analyzer_arn,
            tags=tags_in_db
        )
        print("tag_resource_response in update_analyzer_tags is ", tag_resource_response)

        send_response_dict['responseStatus'] = 'SUCCESS'
        send_response_dict['responseData'] = 'SUCCESS'

        return send_response_dict
    except Exception as e:
        print('An Error occurred in update_analyzer_tags', e)
        send_response_dict['responseStatus'] = 'FAILED'
        send_response_dict['responseData'] = 'Error in update_analyzer_tags - {}'.format(e)
        return send_response_dict


def cleanup_resources(analyzer_db_table_name, analyzer_name):
    try:
        send_response_dict = {'responseStatus': 'FAILED', 'responseData': 'FAILED'}

        ### Delete DynamoDB table
        delete_table_response = ddb_client.delete_table(
            TableName=analyzer_db_table_name
        )
        print("delete_table_response is ", delete_table_response)
        if delete_table_response['ResponseMetadata']['HTTPStatusCode'] in [200, 201, 202, 204, 206]:
            send_response_dict['responseStatus'] = 'SUCCESS'
            send_response_dict['responseData'] = 'SUCCESS'
        else:
            send_response_dict['responseStatus'] = 'FAILED'
            send_response_dict['responseData'] = 'FAILED'
         
        
        delete_analyzer_response = client.delete_analyzer(
            analyzerName=analyzer_name
        )
        print("delete_analyzer_response is ", delete_analyzer_response)
        if delete_analyzer_response['ResponseMetadata']['HTTPStatusCode'] in [200, 201, 202, 204, 206]:
            send_response_dict['responseStatus'] = 'SUCCESS'
            send_response_dict['responseData'] = 'SUCCESS'
        else:
            send_response_dict['responseStatus'] = 'FAILED'
            send_response_dict['responseData'] = 'FAILED'

        return send_response_dict

    except Exception as e:
        print('An Error occurred in cleanup_resources', e)
        send_response_dict['responseStatus'] = 'FAILED'
        send_response_dict['responseData'] = 'Error in cleanup_resources - {}'.format(e)
        return send_response_dict


def lambda_handler(event, context):
    print('Event Received - ',event)
    print('Context Received - ',context)
    request_type = event['RequestType']
    lambda_result = None
    function_name = context.function_name

    analyzer_region = os.environ['STACK_REGION']
    analyzer_account = os.environ['EXECUTION_ACCOUNT']
    analyzer_base_name = os.environ['ANALYZER_NAME']
    analyzer_name = analyzer_base_name + "-" + analyzer_region + "-" + analyzer_account
    print("analyzer_name in handler is ", analyzer_name)
    analyzer_type = os.environ['ANALYZER_TYPE']
    tbl_name = 'dxcms-iam-access-analyzer'
    partition_key = 'AccessAnalyzerName'
    partition_value = analyzer_name 
    send_response_dict = {'responseStatus': 'FAILED', 'responseData': 'FAILED'}

    ###  process Delete event
    if request_type in ['Delete'] and ('ServiceToken' in event):
        print("Processing Delete event in lambda_handler")
        try:

            ### delete access analyzer and access analyzer DynamoDB item 

            analyzer_db_table_name = 'dxcms-iam-access-analyzer'
            send_response_dict = {'responseStatus': 'FAILED', 'responseData': 'FAILED'}
            send_response_dict =  cleanup_resources(analyzer_db_table_name, analyzer_name)
            if send_response_dict['responseStatus'] == 'FAILED':
                return(send_response(event, context, send_response_dict['responseStatus'], send_response_dict['responseData'],None, None, send_response_dict['responseData']))
            print("send_response_dict from cleanup_resources is ", send_response_dict)


        except Exception as e:
            print('Error - ',e)
            send_response_dict['responseStatus'] = 'FAILED'
            send_response_dict['responseData'] = e 

    ###  process Create event
    if request_type in ['Create'] and ('ServiceToken' in event):
        try:
            ### create DynamoDB table
            create_db_table_response, send_response_dict = create_analyzer_db_table()
            if send_response_dict['responseStatus'] == 'FAILED':
                return send_response(event, context, send_response_dict['responseStatus'], send_response_dict['responseData'],None, None, send_response_dict['responseData'])

            create_default_db_items_response, send_response_dict = create_default_db_items(analyzer_name, tbl_name, function_name)
            if send_response_dict['responseStatus'] == 'FAILED':
                return send_response(event, context, send_response_dict['responseStatus'], send_response_dict['responseData'],None, None, send_response_dict['responseData'])

            get_db_item_response, send_response_dict = get_db_item(tbl_name, partition_key, partition_value, sort_key=None, sort_value=None)
            print("get_db_item_response is ", get_db_item_response)

            ### create access analyzer

            archive_rule = get_db_item_response['Item']['external-access-analyzer-archive-rule']
            print("archive_rule in handler before create analyzer is ", archive_rule)
            create_access_analyzer_fcn_response, send_response_dict = create_access_analyzer(analyzer_name, analyzer_type, archive_rule, function_name)
            if send_response_dict['responseStatus'] == 'FAILED':
                return(send_response(event, context, send_response_dict['responseStatus'], send_response_dict['responseData'],None, None, send_response_dict['responseData']))
            print("create_access_analyzer_fcn_response is ", create_access_analyzer_fcn_response)

            #send_response_dict['responseStatus'] = 'SUCCESS'
            #send_response_dict['responseData'] = 'SUCCESS'

        except Exception as e:
            print('Error - ',e)
            send_response_dict['responseStatus'] = 'FAILED'
            send_response_dict['responseData'] = e 

    ###  process stack Update event

    #if request_type in ['Update'] and ('ServiceToken' in event):
    if event['RequestType'] == 'Update':
        try:
            print("Processing Update event")

            ### get_db_rule
            get_db_item_response, send_response_dict = get_db_item(tbl_name, partition_key, partition_value, sort_key=None, sort_value=None)
            print("get_db_item_response in get_db_rule is ", get_db_item_response)
            print("send_response_dict in get_db_rule is ", send_response_dict)
            if send_response_dict['responseStatus'] == 'SUCCESS':
                db_archive_rule = get_db_item_response['Item']['external-access-analyzer-archive-rule']
                print("db_archive_rule in handler update is ", db_archive_rule)
                tags_in_db = get_db_item_response['Item']['external-access-analyzer-tags']
                print("tags_in_db is ", tags_in_db)

            ### get_ext_anal_rules
            get_ext_anal_rules_response, send_response_dict =  get_ext_anal_rules(analyzer_name)
            if send_response_dict['responseStatus'] == 'FAILED':
                return(send_response(event, context, send_response_dict['responseStatus'], send_response_dict['responseData'],None, None, send_response_dict['responseData']))
            print("get_ext_anal_rules_response in handler update is ", get_ext_anal_rules_response)

            ### compare and update attribute 
            
            send_response_dict = update_analyzer(get_db_item_response, get_ext_anal_rules_response, analyzer_name)
            print("send_response_dict in handler for compare and update attributes is ", send_response_dict)

            ### compare and update tags
            send_response_dict = update_analyzer_tags(tags_in_db, analyzer_name)
            if send_response_dict['responseStatus'] == 'FAILED':
                return(send_response(event, context, send_response_dict['responseStatus'], send_response_dict['responseData'],None, None, send_response_dict['responseData']))

        except Exception as e:
            print('Error - ',e)
            send_response_dict['responseStatus'] = 'FAILED'
            send_response_dict['responseData'] = e 


    ### End lambda, send final status to the stack
    print("end of lambda handler")
    print("send_response_dict['responseStatus'] is ", send_response_dict['responseStatus'])
    print("send_response_dict['responseData'] is ", send_response_dict['responseData'])
    send_response(event, context, send_response_dict['responseStatus'], send_response_dict['responseData'],None, None, send_response_dict['responseData'])
