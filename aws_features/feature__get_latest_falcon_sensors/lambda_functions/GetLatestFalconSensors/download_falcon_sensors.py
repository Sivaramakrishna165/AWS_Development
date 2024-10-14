import boto3, json, os
import urllib3, urllib, urllib.parse
from get_post_methods import get_method, post_method
import http.client

SSMFalconGenerateTokenAPI = os.environ['SSMFalconGenerateTokenAPI']
SSMFalconDownloadSensorAPI = os.environ['SSMFalconDownloadSensorAPI']
pDXCS3CustomerBucketName = os.environ['pDXCS3CustomerBucketName']
DXCAWSMSSecretKey = os.environ['DXCAWSMSSecretKey']

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

# Main Methos to execute the Lambda   
def handler(event, context):
    print('Event Received: ', event)
    s3_windows_file_format = 'deploy/externs/{platform}/{filename}'
    s3_linux_file_format = 'deploy/externs/{platform}/{os}/{version}/{filename}'
    
    # Get the required details from ssm params
    secret = get_crowdstrike_secrets()
    GenerateTokenAPI = get_ssm_params(SSMFalconGenerateTokenAPI)
    DownloadSensorAPI = get_ssm_params(SSMFalconDownloadSensorAPI)
    
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
        
    DownloadSensorAPI = DownloadSensorAPI.format(sha=event['Falcon']['sha256'])
    if(event['Platform'] == 'Windows'):
        key = s3_windows_file_format.format(platform=event['Platform'].lower(),filename=event['Falcon']['name'])
    if(event['Platform'] == 'Linux'):
        key = s3_linux_file_format.format(platform=event['Platform'].lower(),os=event['OS'].lower().replace(' ','-'),version=event['Version'],filename=event['Falcon']['name'])
    
    s3_client = boto3.client('s3')
    http=urllib3.PoolManager()
    s3_client.upload_fileobj(http.request('GET', DownloadSensorAPI, headers=headers, preload_content=False), pDXCS3CustomerBucketName, key)
    
    print('Falcon sensors uploaded for {} in location s3://{}/{}'.format(event['Platform'],pDXCS3CustomerBucketName, key))

    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }
