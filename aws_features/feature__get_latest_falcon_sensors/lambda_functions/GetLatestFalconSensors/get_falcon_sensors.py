import boto3
import os
import urllib3
import urllib, urllib.parse
import json
from get_post_methods import get_method, post_method
import http.client

SSMFalconWinGetSensorAPI = os.environ['SSMFalconWinGetSensorAPI']
SSMFalconLinuxGetSensorAPI = os.environ['SSMFalconLinuxGetSensorAPI']
SSMFalconAmazonLinuxGetSensorAPI = os.environ['SSMFalconAmazonLinuxGetSensorAPI']
SSMFalconAmazonLinuxArmGetSensorAPI = os.environ['SSMFalconAmazonLinuxArmGetSensorAPI']
SSMFalconGenerateTokenAPI = os.environ['SSMFalconGenerateTokenAPI']
pDXCS3CustomerBucketName = os.environ['pDXCS3CustomerBucketName']
DXCAWSMSSecretKey = os.environ['DXCAWSMSSecretKey']
DownloadLatestSensorsLambda = os.environ['DownloadLatestSensorsLambda']

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
        except:
            print("Failed to send the response to the provided URL")
    return response

# Get Crowstrike client_id & client_secret
def get_crowdstrike_secrets():
    try:
        secrets = boto3.client('secretsmanager')
        response = secrets.get_secret_value(SecretId=DXCAWSMSSecretKey)
        response = json.loads(response['SecretString'])
        return response
    except Exception as e:
        print('get_crowdstrike_secrets() - ', e)
        raise

# Get ssm Params
def get_ssm_params(name):
    try:
        ssm = boto3.client('ssm')
        response = ssm.get_parameter(Name=name)
        return ssm.get_parameter(Name=name)['Parameter']['Value']
    except Exception as e:
        print('get_ssm_params() - ', e)
        raise

# Get all the OS types from ami-catalog.json
def get_os_form_catalog(platform):
    try:
        s3_client = boto3.client('s3')
        response = s3_client.get_object(Bucket=pDXCS3CustomerBucketName, Key='deploy/utilities/ami-catalog.json')
        images = json.loads(response["Body"].read().decode())
        catalog_os_types = set(dic['OS'].lower() for dic in images['Images'] if dic['Region'] == 'us-east-1' and not isinstance(dic['ImageId'],list))
        awsms_os_types = {}
        for os in catalog_os_types:
            if(platform == 'Linux'):
                if('sles' in os):
                    if 'SLES' not in awsms_os_types: awsms_os_types['SLES'] = []
                    awsms_os_types['SLES'].append(os.replace('sles','').split('-')[0])                
                elif('amazon-linux' in os):
                    if 'Amazon Linux' not in awsms_os_types: awsms_os_types['Amazon Linux'] = []
                    awsms_os_types['Amazon Linux'].append(os.replace('amazon-linux',''))
                elif('oracle' in os):
                    if 'Oracle' not in awsms_os_types: awsms_os_types['Oracle'] = []
                    awsms_os_types['Oracle'].append(os.replace('oracle-linux','').split('.')[0])
                elif('rhel' in os):
                    if 'RHEL' not in awsms_os_types: awsms_os_types['RHEL'] = []
                    awsms_os_types['RHEL'].append(os.replace('rhel','').split('.')[0])
                elif('ubuntu' in os):
                    if 'Ubuntu' not in awsms_os_types: awsms_os_types['Ubuntu'] = []
                    awsms_os_types['Ubuntu'].append(os.replace('ubuntu','').split('.')[0])
            
            if(platform == 'Windows'):
                if('win' in os):
                    if 'Windows' not in awsms_os_types: awsms_os_types['Windows'] = []
                    awsms_os_types['Windows'].append(os.replace('win',''))
                    
            
        for os in awsms_os_types:
            awsms_os_types[os] = set(awsms_os_types[os])

        return awsms_os_types

    except Exception as e:
        print('get_os_form_catalog() -', e)
        raise

# Send reponse to Custom resource
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
        except:
            print("Failed to send the response to the provided URL")
    return response

# Main Methos to executethe Lambda   
def handler(event, context):
    print('Event Received: ', event)
    if('ResourceProperties' in event):
        platform = event['ResourceProperties']['Platform']
    else:
        platform = event['Platform']

    response = {}
    if ('ServiceToken' in event):            
        response['Status'] = 'SUCCESS'
        response['Reason'] = 'See the details in CloudWatch Log Stream: ' + context.log_stream_name
        response['PhysicalResourceId'] = context.log_stream_name
        response['StackId'] = event['StackId']
        response['RequestId'] = event['RequestId']
        response['LogicalResourceId'] = event['LogicalResourceId']
        response['NoEcho'] = False    
    
        send_response(event, response, status='SUCCESS', reason='Lambda Invoked')
        if(event['RequestType'] in ['Delete','Update']):
            # Nothing to do , just return the lambda
            return "Nothing to Do. Lambda Invoked Successfully"
    
    # Get the required details from ssm params
    secret = get_crowdstrike_secrets()
    LinuxGetSensorAPI = get_ssm_params(SSMFalconLinuxGetSensorAPI)
    AmazonLinuxGetSensorAPI = get_ssm_params(SSMFalconAmazonLinuxGetSensorAPI)
    AmazonLinuxArmGetSensorAPI = get_ssm_params(SSMFalconAmazonLinuxArmGetSensorAPI)
    WinGetSensorAPI = get_ssm_params(SSMFalconWinGetSensorAPI)
    GenerateTokenAPI = get_ssm_params(SSMFalconGenerateTokenAPI)
    
    data = {
        'username':secret['crowdstrike_client_id'],
        'password':secret['crowdstrike_client_secret'],
        'grant_type':'client_credentials'
       }

    headers={             
            "Content-Type":"application/x-www-form-urlencoded",
            "Accept":"application/json"
        }
    
    body=urllib.parse.urlencode(data)
    resp = post_method(GenerateTokenAPI, headers=headers, body=body)

    token = json.loads(resp)
    access_token = "{} {}".format(token['token_type'], token['access_token'])
    
    headers={             
            "Authorization":access_token,
            "Accept":"application/json"
        }

    falcon_sensors = {}
    lambda_client = boto3.client('lambda')
    awsms_os_types = get_os_form_catalog(platform)
    print('OS Version available in ami-catalog.json ', awsms_os_types)
    if platform == 'Windows':
        for os in awsms_os_types:
            invoke_lambda_event = {}
            response = json.loads(get_method(WinGetSensorAPI,headers)) 
            falcon_sensors[os] = response['resources'][0]
            
            invoke_lambda_event['Platform'] = 'Windows'
            invoke_lambda_event['Falcon'] = response['resources'][0]
            res = lambda_client.invoke(FunctionName=DownloadLatestSensorsLambda,
                                    InvocationType='Event',
                                    Payload=json.dumps(invoke_lambda_event))
            print(res)

    if platform == 'Linux':
        for os in awsms_os_types:
            falcon_sensors[os] = {}
            for version in awsms_os_types[os]:
                falcon_sensors[os][version]  = {}
                print('os:{} & Version:{}'.format(os, version))

                if os == 'Amazon Linux' and version == '2-arm':
                    version = '2 - arm64'
                    response = json.loads(get_method(AmazonLinuxArmGetSensorAPI,headers))
                    flt_resp = list(filter(lambda x: version in x['os_version'].split('/') , response['resources']))
                elif os == 'Amazon Linux' and version == '2023-arm':
                    version = '2023 - arm64'
                    response = json.loads(get_method(AmazonLinuxArmGetSensorAPI,headers))
                    flt_resp = list(filter(lambda x: version in x['os_version'].split('/') , response['resources']))
                elif os == 'Amazon Linux' and version == '2-x86':
                    version = '2'
                    response = json.loads(get_method(AmazonLinuxGetSensorAPI.format(os_ver=version),headers))
                    flt_resp = list(filter(lambda x: version in x['os_version'].split('/') , response['resources']))
                elif os == 'Amazon Linux' and version == '2023-x86':
                    version = '2023'
                    response = json.loads(get_method(AmazonLinuxGetSensorAPI.format(os_ver=version),headers))
                    flt_resp = list(filter(lambda x: version in x['os_version'].split('/') , response['resources']))
                else:
                    response = json.loads(get_method(LinuxGetSensorAPI.format(os=os),headers))
                    # filter to extract only amd64
                    flt_resp = list(filter(lambda x: 'arm64' not in x['os_version'] , list(filter(lambda x: 'IBM zLinux' not in x['os_version'], list(filter(lambda x: version in x['os_version'].split('/') , response['resources']))))))
                
                # flt_resp = list(filter(lambda x: 'arm64' not in x['os_version'] ,list(filter(lambda x: version in x['os_version'].split('/') , response['resources']))))
                
                if(flt_resp):
                    falcon_sensors[os][version]  = flt_resp[0]
                    invoke_lambda_event = {}
                    invoke_lambda_event['Platform'] = 'Linux'
                    invoke_lambda_event['OS'] = os
                    invoke_lambda_event['Version'] = version
                    invoke_lambda_event['Falcon'] = flt_resp[0]
                    
                    lambda_client.invoke(FunctionName=DownloadLatestSensorsLambda,
                                            InvocationType='Event',
                                            Payload=json.dumps(invoke_lambda_event))
    
    print('Falcon sensors for {} - {}'.format(platform, falcon_sensors))
    

    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }
