import boto3
from time import sleep
import json
import urllib.parse
import http.client
import os

def lambda_handler(event,context):
    
    print("Received event: ",event)
    response = {}
    response['Status'] = 'SUCCESS'
    response['Reason'] = 'See the details in CloudWatch Log Stream: ' + context.log_stream_name
    response['PhysicalResourceId'] = context.log_stream_name
    response['StackId'] = event['StackId']
    response['RequestId'] = event['RequestId']
    response['LogicalResourceId'] = event['LogicalResourceId']
    response['NoEcho'] = False

    pusername=os.environ["PUSERNAME"]

    if (event['RequestType'] in ['Create','Update']) and ('ServiceToken' in event):
        sts_client = boto3.client('sts')
        quicksight_client = boto3.client('quicksight')
        acc_id = sts_client.get_caller_identity()['Account']
        quicksight_name='quicksight-cid-{}'.format(acc_id)
        status=describe_quicksight_account(quicksight_client,acc_id)
        
        if not status:
            sleep(10)
            notification_email=event['ResourceProperties']['customer_email']
            create_quicksight_account(quicksight_client,acc_id,quicksight_name,notification_email)
            #sleep(100)
            #register_user(quicksight_client,email_id,acc_id)
            send_response(event, response, status='SUCCESS', reason='Create event received')
        elif pusername=="":
            send_response(event, response, status='FAILED', reason='Quicksight account already exist. provide the admin user name in parameters')
        else:
            send_response(event, response, status='SUCCESS', reason='Create event received')


    if (event['RequestType'] in ['Delete']) and ('ServiceToken' in event):
        send_response(event, response, status='SUCCESS', reason='Delete event received')
 
#To send the response back to cfn template.
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
    
def create_quicksight_account(client,account_id,account_name,notification_email):
    try:
        response = client.create_account_subscription(Edition='ENTERPRISE',
        AuthenticationMethod='IAM_AND_QUICKSIGHT',
        AwsAccountId=account_id,
        AccountName=account_name,
        NotificationEmail=notification_email,
        EmailAddress=notification_email)
        sleep(60)
        print("Quicksight account {} created successfully".format(account_name))
    except Exception as e:
        print("Quicksight account {} creation failed with error: {}".format(account_name,e))
"""
def register_user(client,email_id,account_id):
    try:
        response = client.register_user(
        IdentityType='QUICKSIGHT',
        Email=email_id,
        UserRole='ADMIN',
        AwsAccountId=account_id,
        Namespace='default',
        UserName=email_id)
        print("User {} added successfully".format(email_id))
    except Exception as e:
        print("User creation {} failed with error: {}".format(email_id,e))"""
    
def describe_quicksight_account(client,account_id):
    try:
        response = client.describe_account_subscription(AwsAccountId=account_id)
        try:
            if "ACCOUNT_CREATED" == response["AccountInfo"]["AccountSubscriptionStatus"]:
                print("Quicksight account already present with name {}. Skipping account creation".format(response["AccountInfo"]["AccountName"]))
                return True
            else:
                return False
        except Exception as e:
            return False
    except Exception as e:
        return False
        print(e)
        