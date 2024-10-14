'''
GetWorkloadvpcVpcid will 1) obtain the VPC Id of the offering WorkloadVPC v2 and the subnet Id for "Private Workload A", and 2) return both 
'''
import boto3
import http.client
import urllib.parse
import json
ec2_client = boto3.client('ec2')

def send_response(request, response, status=None, reason=None):
    if status is not None:
        response['Status'] = status
    if reason is not None:
        response['Reason'] = reason
    if 'ResponseURL' in request and request['ResponseURL']:
        try:
            url = urllib.parse.urlparse(request['ResponseURL'])
            body = json.dumps(response)
            print('Body - ', body)
            https = http.client.HTTPSConnection(url.hostname)
            https.request('PUT', url.path + '?' + url.query, body)
            print('HTTP response sent successfully')
        except:
            print("Failed to send the response to the provided URL")
    return response

def get_wlvpc_vpcid():
    try:
        print("getting vpcid")
        describe_vpcs_response = ec2_client.describe_vpcs(
            Filters=[
                {
                    'Name': 'tag:Owner',
                    'Values': [
                        'DXC'
                    ]
                },
                {
                    'Name': 'tag:Name',
                    'Values': [
                        'Workload VPC v2'
                    ]
                }
            ],
            DryRun=False
        )
        print("describe_vpcs_response is ", describe_vpcs_response)
        
        VPC_ID = describe_vpcs_response['Vpcs'][0]['VpcId']
        print("VPC_ID is ", VPC_ID)
        return VPC_ID
    except Exception as e:
        print("Error in get_wlvpc_vpcid-",e)

def get_mnt_tgt_sub_id():
    print("getting mount target subnet Id - Workload VPC subnet Priv Workload A")
    try:
        describe_subnets_response = ec2_client.describe_subnets(
            Filters=[
                    {
                        'Name': 'tag:Name',
                        'Values': [
                            'Private Workload A'
                        ]
                    },
                ],
            DryRun=False
        )

        HttpStatus = describe_subnets_response['ResponseMetadata']['HTTPStatusCode']
        print("describe_subnets_response in get_mnt_tgt_sub_id is ", describe_subnets_response)
        ###Subnet_Id = describe_vpcs_response['Vpcs'][0]['VpcId']
        Subnet_Id = describe_subnets_response['Subnets'][0]['SubnetId']
        return Subnet_Id

    except Exception as e:
        print("Error in get_mnt_tgt_sub_id-",e)

def lambda_handler(event, context):
    print('Event Received - ',event)
    print('Context Received - ',context)
    request_type = event['RequestType']
    print("request_type is ", request_type)

    response = {}
    if (event['RequestType'] in ['Create','Update','Delete']) and ('ServiceToken' in event):            
        print("defining response")
        response['Status'] = 'SUCCESS'
        response['Reason'] = 'See the details in CloudWatch Log Stream: ' + context.log_stream_name
        response['PhysicalResourceId'] = 'CustomResourcePhysicalID'
        response['StackId'] = event['StackId']
        response['RequestId'] = event['RequestId']
        response['LogicalResourceId'] = event['LogicalResourceId']
        response['NoEcho'] = False
        response['Data'] = {}

    ###  process Delete event
    if (event['RequestType'] in ['Delete']) and ('ServiceToken' in event):
        send_response(event, response, status='SUCCESS', reason='Delete event received')


    ###  process Create event
    if request_type in ['Create'] and ('ServiceToken' in event):
        try:
            print("calling get_wlvpc_vpcid")
            get_wlvpc_vpcid_response = get_wlvpc_vpcid()
            print("get_wlvpc_vpcid_response is ", get_wlvpc_vpcid_response)
            response['Data']['WlvpcVpcid'] = get_wlvpc_vpcid_response

            print("calling get_mnt_tgt_sub_id")
            get_mnt_tgt_sub_id_response = get_mnt_tgt_sub_id()
            print("get_mnt_tgt_sub_id_response is ", get_mnt_tgt_sub_id_response)
            response['Data']['MntTgtSubId'] = get_mnt_tgt_sub_id_response 
            print("response['Data'] is ", response['Data'])
            send_response(event, response, status='SUCCESS', reason='Lambda Invoked')
       
            return {
                    'statusCode': 200,
                    #'body': get_wlvpc_vpcid_response
                    'body': response['Data']
                }
        except:
            response['Status'] = 'FAILED'
            response['Data']['WlvpcVpcid'] = 'FAILED' 
            send_response(event, response, status='FAILED', reason='Error getting vpcid from lambda handler')


    else:
        print("skipping try statement")
