import boto3
import json
import urllib.parse
import http.client

config_client = boto3.client('config')

def describe_configuration_recorder():
    try:
        response = config_client.describe_configuration_recorders()
        recorders = response.get('ConfigurationRecorders', [])
        if recorders:
            return recorders[0]['name'], recorders[0]['roleARN']
        else:
            return None, None
    except Exception as e:
        print(f'Error describing configuration recorder: {e}')
        return None, None

def update_configuration_recorder(exclusion_list):
    try:
        recorder_name, role_arn = describe_configuration_recorder()
        print("recorder_name:", recorder_name)
        print("role_arn:", role_arn)

        if recorder_name:
            config_recorder_params = {
                'ConfigurationRecorder': {
                    'name': recorder_name,
                    'roleARN': role_arn,
                    'recordingGroup': {
                        'allSupported': False,
                        'includeGlobalResourceTypes': False,
                        'exclusionByResourceTypes': {
                            'resourceTypes': exclusion_list
                        },
                        'recordingStrategy': {
                            'useOnly': 'EXCLUSION_BY_RESOURCE_TYPES'
                        }
                    }
                }
            }

            response = config_client.put_configuration_recorder(**config_recorder_params)
            print('Configuration recorder updated successfully.')
            return response
        else:
            print('No configuration recorder found.')
            return None
    except Exception as e:
        print(f'Error updating configuration recorder: {e}')
        return None

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

def fetch_parameter_from_dynamodb():
    try:
        dynamodb = boto3.client('dynamodb')
        response = dynamodb.get_item(
            TableName='AccountFeatureDefinitions',
            Key={'Feature': {'S': 'ConfigServiceWithExclusion'}}
        )
        feature_params = response.get('Item', {}).get('FeatureParams', {})
        exclusion_map = feature_params.get('M', {}).get('pFtConfServResourceListToSkip', {}).get('M', {})
        exclusion_default = exclusion_map.get('Default', {}).get('S', '')

        if exclusion_default:
            return exclusion_default.split(',')
        else:
            return []
    except Exception as e:
        print(f'Error fetching parameter from DynamoDB: {e}')
        raise


def lambda_handler(event, context):
    print("Received event: ", event)
    response = {}
    response['Status'] = 'SUCCESS'
    response['Reason'] = 'See the details in CloudWatch Log Stream: ' + context.log_stream_name
    response['PhysicalResourceId'] = 'StaticPhysicalResourceId'
    response['StackId'] = event['StackId']
    response['RequestId'] = event['RequestId']
    response['LogicalResourceId'] = event['LogicalResourceId']
    response['NoEcho'] = False

    # Retrieve exclusion list from DynamoDB
    exclusion_list = fetch_parameter_from_dynamodb()
    print("Exclusion List:", exclusion_list)

    try:
        if (event['RequestType'] in ['Create', 'Update']) and ('ServiceToken' in event):
            if not exclusion_list or any(e.strip().lower() == "blank" for e in exclusion_list):
                print("Invalid resource type. Skipping the process.")
                send_response(event, response, status='SUCCESS', reason='Invalid resource type')
            else:
                try:
                    update_configuration_recorder(exclusion_list)
                    send_response(event, response, status='SUCCESS',
                                  reason='Configuration recorder updated successfully')
                except Exception as e:
                    print(f'Error updating configuration recorder: {e}')
                    response['Error'] = str(e)
                    send_response(event, response, status='FAILED', reason="Failed to update recorder")

        elif event['RequestType'] == 'Delete' and 'ServiceToken' in event:
            send_response(event, response, status='SUCCESS', reason='Delete event received')

    except Exception as e:
        print(f'Lambda Execution Error: {e}')

    return {'Lambda executed statusCode': 200}




