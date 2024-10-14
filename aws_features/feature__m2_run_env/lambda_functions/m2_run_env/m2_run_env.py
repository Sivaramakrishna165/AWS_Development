'''
m2_run_env.py will perform the following:
    - Upon Offering deployment, EnableFeature is False, feature__m2_run_env will not be deployed, and M2RunEnv item is created in the AccountFeatureDefinitions DynamoDB table
    - Once the parameters are updated or the defaults accepted, EnableFeature set to true, and ses-standards-master stack is updated, the feature will be deployed.
    - If the current region supports M2
         if pCreateEfs is True (the default)
             create an EFS filesystem and update the DB
         else
             skip EFS filesystem creation
             user responsible for populating pEfsId with the Id of an already created filesystem
         if pFindSubnets is True (the default)
             the Offering Workload VPC private subnet Ids and the associated
               security group will be located and the DB parameters
               pM2EnvSubnet1, pM2EnvSubnet2, and pSecurityGroupIds will be populated.
         else
             pFindSubnets is false and the user must populate
               pM2EnvSubnet1, pM2EnvSubnet2, and pSecurityGroupIds
               with the desired Ids prior to feature deployment so that customer provided subnets may be used instead of Offering subnets.
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

### Note: all of the waitcounts must be less than the lambda timeout value
logger = logging.getLogger()
logger.setLevel(logging.INFO)

config=Config(retries=dict(max_attempts=10,mode='standard'))
dynamodb_resource = boto3.resource('dynamodb', config=config)
target_table='AccountFeatureDefinitions'
feature_name='M2RunEnv'

http = urllib3.PoolManager()
SUCCESS = "SUCCESS"
FAILED = "FAILED"

ec2_client = boto3.client('ec2', config=config)
mainframe_client = boto3.client('m2', config=config)
efs_client = boto3.client('efs', config=config)

AwsRegion = os.environ['Aws_Region']
AwsAccount = os.environ['Aws_Account']

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
            #'Data' : {'Cron':responseData}
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

def get_workloadvpc_priv_subnets(ec2_client):

    try:
        send_response_dict = {'responseStatus': 'FAILED', 'responseData': 'FAILED'}
        subnets_list_placeholder = []
        subnets_list = []
        describe_subnets_response = ec2_client.describe_subnets(
            Filters=[
                    {
                        'Name': 'tag:Name',
                        'Values': [
                            'Private Workload A',
                            'Private Workload B'
                        ]
                    },
                ],
            DryRun=False
        )

        HttpStatus = describe_subnets_response['ResponseMetadata']['HTTPStatusCode']
        print("###")
        print("describe_subnets_response['ResponseMetadata']['HTTPStatusCode'] is ", describe_subnets_response['ResponseMetadata']['HTTPStatusCode'])
        print("First HttpStatus print in get_workloadvpc_priv_subnets is ", HttpStatus)
        print("###")
        if HttpStatus == 200 or HttpStatus == 202:
            send_response_dict['responseStatus'] = 'SUCCESS'
            send_response_dict['responseData'] = 'get_sg'
        else:
            send_response_dict['responseStatus'] = 'FAILED'
            send_response_dict['responseData'] = 'Error in get_workloadvpc_priv_subnets'
            return subnets_list_placeholder, describe_subnets_response, send_response_dict

        if describe_subnets_response['Subnets']:
            for subnet in describe_subnets_response['Subnets']:
                subnets_list.append(subnet['SubnetId'])
            if len(subnets_list) == 2 and (send_response_dict['responseStatus'] == 'SUCCESS'):
                print("Second HttpStatus print in get_workloadvpc_priv_subnets is ", HttpStatus)
                send_response_dict['responseStatus'] = 'SUCCESS'
                send_response_dict['responseData'] = 'get_sg'
            else:
                send_response_dict['responseStatus'] = 'FAILED'
                send_response_dict['responseData'] = 'Error in get_workloadvpc_priv_subnets'
            return subnets_list, describe_subnets_response, send_response_dict
        else:
            print("No WorkloadVPC v2 private subnets exist")
            send_response_dict['responseStatus'] = 'FAILED'
            send_response_dict['responseData'] = 'Error in get_workloadvpc_priv_subnets'
            return subnets_list, describe_subnets_response, send_response_dict


    except Exception as e:
        print('An Error occurred locating Offering WorkloadVPC v2 subnets', e)
        send_response_dict['responseStatus'] = 'FAILED'
        send_response_dict['responseData'] = 'Error in get_workloadvpc_priv_subnets - {}'.format(e)
        return subnets_list, describe_subnets_response, send_response_dict



def get_sg(ec2_client, subnets_response):
    try:
        send_response_dict = {'responseStatus': 'FAILED', 'responseData': 'FAILED'}
        wVpcId = subnets_response['Subnets'][0]['VpcId']
        sec_group_response = ec2_client.describe_security_groups(
            Filters=[
                {
                    'Name': 'vpc-id',
                    'Values': [
                        wVpcId,
                    ]
                },
                {
                    'Name': 'group-name',
                    'Values': [
                        'default',
                    ]
                },
            ],
        )
        sg_response_list = sec_group_response['SecurityGroups']
        # only one default SG exists for Workload VPC v2 so use index 0
        workload_def_sg = sg_response_list[0]['GroupId']

        HttpStatus = sec_group_response['ResponseMetadata']['HTTPStatusCode']
        print("HttpStatus in get_sg is ", HttpStatus)
        if HttpStatus == 200 or HttpStatus == 202:
            send_response_dict['responseStatus'] = 'SUCCESS'
            send_response_dict['responseData'] = 'get_sg'
        else:
            send_response_dict['responseStatus'] = 'FAILED'
            send_response_dict['responseData'] = 'Error in get_sg'
        return workload_def_sg, send_response_dict

    except Exception as e:
        print('An Error occurred in get_sg', e)
        send_response_dict['responseStatus'] = 'FAILED'
        send_response_dict['responseData'] = 'Error in get_sg - {}'.format(e)
        return 'FAILED', send_response_dict


def get_afd_params(dynamodb_resource, target_table, feature_name):
    try:
        send_response_dict = {'responseStatus': 'FAILED', 'responseData': 'FAILED'}
        table = dynamodb_resource.Table(target_table)
        get_item_response = table.get_item(Key={"Feature":feature_name})
        print("get_item_response is ", get_item_response)
        afd_item = get_item_response['Item']
        param_dict = get_item_response['Item']['FeatureParams']
        # (set responseStatus from HTTPStatusCode and also return responseStatus)
        HttpStatus = get_item_response['ResponseMetadata']['HTTPStatusCode']
        if HttpStatus == 200 or HttpStatus == 202:
            send_response_dict['responseStatus'] = 'SUCCESS'
            send_response_dict['responseData'] = 'get_afd_params'
        else:
            send_response_dict['responseStatus'] = 'FAILED'
            send_response_dict['responseData'] = 'Error in get_afd_params'
        return param_dict, send_response_dict, afd_item

    except Exception as e:
        print("Error in get_afd_params-",e)
        send_response_dict['responseStatus'] = 'FAILED'
        send_response_dict['responseData'] = 'Error in get_afd_params - {}'.format(e)
        return 'FAILED', send_response_dict, afd_item


def create_efs(final_db_params_dict, efs_client):
    try:
        send_response_dict = {'responseStatus': 'FAILED', 'responseData': 'FAILED'}
        EfsPerformanceMode = final_db_params_dict['pEfsPerformanceMode']['Default']
        EfsEncryption = final_db_params_dict['pEfsEncryption']['Default']
        EfsThroughputMode = final_db_params_dict['pEfsThroughputMode']['Default']
        EfsProvisionedThroughputInMibps = int(final_db_params_dict['pEfsProvisionedThroughputInMibps']['Default'])
        EfsBackup = final_db_params_dict['pEfsBackup']['Default']
        # ensure tag_list is of type list
        #tag_list = [ { 'Key': 'Owner', 'Value': 'DXC' } ]
        EfsTagIn = final_db_params_dict['pEfsTagList']['Default']
        EfsTagIn = EfsTagIn.replace("'",'"')
        print("EfsTagIn is ", EfsTagIn)
        EfsTagsDict = json.loads(EfsTagIn)
        print("EfsTagsDict is type ", type(EfsTagsDict))
        EfsTagList = [EfsTagsDict]
        print("EfsTagList is ", EfsTagList)
        print("type of EfsTagList is ", type(EfsTagList))
        SecurityGroupIds = final_db_params_dict['pSecurityGroupIds']['Default']
        M2EnvSubnet1 = final_db_params_dict['pM2EnvSubnet1']['Default']

        ### Create File System

        # for bursting mode, do not include EfsProvisionedThroughputInMibps
        if EfsThroughputMode == 'bursting':
            create_efs_response = efs_client.create_file_system(
                PerformanceMode=EfsPerformanceMode,
                Encrypted=EfsEncryption,
                ThroughputMode=EfsThroughputMode,
                Backup=EfsBackup,
                Tags=EfsTagList
            )
        else:
            # for provisioned mode, MUST include EfsProvisionedThroughputInMibps
            create_efs_response = efs_client.create_file_system(
                PerformanceMode=EfsPerformanceMode,
                Encrypted=EfsEncryption,
                ThroughputMode=EfsThroughputMode,
                ProvisionedThroughputInMibps=EfsProvisionedThroughputInMibps,
                Backup=EfsBackup,
                Tags=EfsTagList
            )

        ### wait for completion

        AwsCreationToken = create_efs_response['CreationToken']
        print("AwsCreationToken is ", AwsCreationToken)
        FileSysId = create_efs_response['FileSystemId']
        print("FileSysId is ", FileSysId)
        LifeCycleState = create_efs_response['LifeCycleState']
        print("LifeCycleState is ", LifeCycleState)

        waitcount = 0
        while(LifeCycleState != 'available' and waitcount <=10):
            try:
                time.sleep(3)
                waitcount +=1
                describe_efs_response = efs_client.describe_file_systems(
                    CreationToken=AwsCreationToken
                )
                LifeCycleState = describe_efs_response['FileSystems'][0]['LifeCycleState']
                print("LifeCycleState is ", LifeCycleState)
                print("waitcount is ", waitcount)
            except Exception as e:
                print("Error creating or getting efs:", e)
                break

        ### Create EFS Mount Target

        SubnetId = M2EnvSubnet1
        SecurityGroups = SecurityGroupIds

        create_mount_target_response = efs_client.create_mount_target(
            FileSystemId=FileSysId,
            SubnetId=SubnetId,
            SecurityGroups=[
               SecurityGroups
            ]
        )

        print("create_mount_target_response is ", create_mount_target_response)

        ### wait for completion

        MntTargetId = create_mount_target_response['MountTargetId']
        if 'fsmt-' not in MntTargetId:
            NumMntTgtCnt = 0
        else:
            NumMntTgtCnt = 1
            print("MntTargetId is ready")

        print("NumMntTgtCnt is ", NumMntTgtCnt)
        waitcount = 0
        while(NumMntTgtCnt == 0 and waitcount <=10):
            try:
                time.sleep(3)
                waitcount +=1
                describe_file_systems_response = efs_client.describe_file_systems(
                    FileSystemId=FileSysId
                )
                print("describe_file_systems_response is ", describe_file_systems_response)
                NumMntTgtCnt = describe_file_systems_response['FileSystems'][0]['NumberOfMountTargets']
                print("NumMntTgtCnt in loop is ", NumMntTgtCnt)
                print("waitcount is ", waitcount)
                print(" ")
            except Exception as e:
                print("Error creating mount targets:", e)
                break



        if LifeCycleState == 'available' and NumMntTgtCnt != 0:
            send_response_dict['responseStatus'] = 'SUCCESS'
            send_response_dict['responseData'] = 'create_efs'
            return FileSysId, send_response_dict
        else:
            raise Exception('Error: FileSysId not located')


    except Exception as e:
        print("Error in create_efs-",e)
        send_response_dict['responseStatus'] = 'FAILED'
        send_response_dict['responseData'] = 'Error in create_efs - {}'.format(e)
        return 'FAILED', send_response_dict

    except boto3.exceptions.botocore.client.ClientError as e:
        print("Client error create_efs: {}  - {}".format(obj_json, str(e)))
        send_response_dict['responseStatus'] = 'FAILED'
        send_response_dict['responseData'] = 'Error in create_efs - {}'.format(e)
        return 'FAILED', send_response_dict


def create_m2_env(mainframe_client, final_db_params_dict, FsId):
    try:
        # Warning - must provide a maintenance window parameter
        send_response_dict = {'responseStatus': 'FAILED', 'responseData': 'FAILED'}

        M2EnvDescription = final_db_params_dict['pM2EnvDescription']['Default']
        M2EngineType = final_db_params_dict['pM2EngineType']['Default']
        HighAvailabilityConfig = int(final_db_params_dict['pHighAvailabilityConfig']['Default'])
        InstanceType = final_db_params_dict['pInstanceType']['Default']
        M2EnvName = final_db_params_dict['pM2EnvName']['Default']
        PublicAccess = final_db_params_dict['pPublicAccess']['Default']
        SecurityGroupIds_orig = final_db_params_dict['pSecurityGroupIds']['Default']
        SecurityGroupIds_list = ast.literal_eval(SecurityGroupIds_orig)
        M2EnvSubnet1 = final_db_params_dict['pM2EnvSubnet1']['Default']
        M2EnvSubnet2 = final_db_params_dict['pM2EnvSubnet2']['Default']
        EfsMountPoint = final_db_params_dict['pEfsMountPoint']['Default']

        # desired maintenance window format: 'wed:03:27-wed:05:27'
        PrefMaintWinDay = final_db_params_dict['pPrefMaintWinDay']['Default']
        PrefMaintWinHrStart = final_db_params_dict['pPrefMaintWinHrStart']['Default']
        PrefMaintWinHrStop = final_db_params_dict['pPrefMaintWinHrStop']['Default']
        PrefMaintWinMin = final_db_params_dict['pPrefMaintWinMin']['Default']

        maint_window = PrefMaintWinDay+':'+PrefMaintWinHrStart+':'+PrefMaintWinMin+'-'+PrefMaintWinDay+':'+PrefMaintWinHrStop+':'+PrefMaintWinMin
        print("maint_window is ", maint_window)

        M2Tags = final_db_params_dict['pM2Tags']['Default']
        M2TagsSwap = M2Tags.replace("'",'"')
        M2TagsDict = json.loads(M2TagsSwap)
        print("M2TagsDict is ", M2TagsDict)
        print("type of M2TagsDict is ", type(M2TagsDict))

        create_env_response = mainframe_client.create_environment(
            description=M2EnvDescription,
            engineType=M2EngineType,
            highAvailabilityConfig={
                'desiredCapacity': HighAvailabilityConfig
            },
            instanceType=InstanceType,
            name=M2EnvName,
            preferredMaintenanceWindow=maint_window,
            publiclyAccessible=PublicAccess,
            securityGroupIds=SecurityGroupIds_list,
            storageConfigurations=[
                {
                    'efs': {
                        'fileSystemId': FsId,
                        'mountPoint': EfsMountPoint
                    }
                }
            ],
            subnetIds=[
                M2EnvSubnet1,
                M2EnvSubnet2
            ],
            tags=M2TagsDict
        )

        print("create_env_response is ", create_env_response)

        ### wait for completion
        EnvStatus = 'InProgress'
        waitcount = 0
        while(EnvStatus != 'Available' and waitcount <=21):
            try:
                time.sleep(20)
                waitcount +=1
                list_env_response = mainframe_client.list_environments(
                    names=[
                        M2EnvName
                    ]
                )
                EnvStatus = list_env_response['environments'][0]['status']
                print("EnvStatus is ", EnvStatus)
                print("waitcount is ", waitcount)
            except Exception as e:
                print("Error listing M2 environment:", e)
                send_response_dict['responseStatus'] = 'FAILED'
                send_response_dict['responseData'] = list_env_response
                raise Exception('Error listing environments')
                break


        ### Send results
        HttpStatus = create_env_response['ResponseMetadata']['HTTPStatusCode']
        if HttpStatus == 200 or HttpStatus == 202:
            send_response_dict['responseStatus'] = 'SUCCESS'
            send_response_dict['responseData'] = create_env_response
        else:
            send_response_dict['responseStatus'] = 'FAILED'
            send_response_dict['responseData'] = create_env_response
        if EnvStatus == 'Available':
            send_response_dict['responseStatus'] = 'SUCCESS'
            send_response_dict['responseData'] = EnvStatus
        else:
            send_response_dict['responseStatus'] = 'FAILED'
            send_response_dict['responseData'] = EnvStatus
        return create_env_response, send_response_dict

    except Exception as e:
        print("Error in create_m2_env-",e)
        send_response_dict['responseStatus'] = 'FAILED'
        send_response_dict['responseData'] = 'Error in create_m2_env - {}'.format(e)
        return 'FAILED', send_response_dict

    except boto3.exceptions.botocore.client.ClientError as e:
        print("Client error create_m2_env: {}  - {}".format(obj_json, str(e)))
        send_response_dict['responseStatus'] = 'FAILED'
        send_response_dict['responseData'] = 'Client Error in create_m2_env - {}'.format(e)
        return 'FAILED', send_response_dict


def format_afd_item_json(work_priv_subnet_list, wvpc_default_sg, afd_item):
    try:
        # if this is called, then pFindSubnets is true
        send_response_dict = {'responseStatus': 'FAILED', 'responseData': 'FAILED'}
        formatted_json = afd_item
        formatted_json['FeatureParams']['pM2EnvSubnet1']['Default'] = work_priv_subnet_list[0]
        formatted_json['FeatureParams']['pM2EnvSubnet2']['Default'] = work_priv_subnet_list[1]
        SecurityGroupIds_orig = formatted_json['FeatureParams']['pSecurityGroupIds']['Default']
        if SecurityGroupIds_orig != 'Dummy':
            # append wvpc_default_sg to the customer provided SG list
            print("SecurityGroupIds_orig is ", SecurityGroupIds_orig)
            # inconsistent results splitting both [] together, so separate
            pSGids_temp1 = SecurityGroupIds_orig.strip('[')
            print("pSGids_temp1 is ", pSGids_temp1)
            pSGids_temp2 = pSGids_temp1.strip(']')
            print("pSGids_temp2 is ", pSGids_temp2)
            pSGids_temp3 = pSGids_temp2 + ',' + "'" + wvpc_default_sg + "'"
            print("pSGids_temp3 is ", pSGids_temp3)
            pSGids_final = '[' + pSGids_temp3 + ']'
            print("pSGids_final is ", pSGids_final)
            formatted_json['FeatureParams']['pSecurityGroupIds']['Default'] = pSGids_final

        else:
            raise Exception('Error: User did not enter the SGs from feature EFS into pSecurityGroupIds in DyamoDB.')

        send_response_dict['responseStatus'] = 'SUCCESS'
        send_response_dict['responseData'] = 'format_afd_item_json'
        return formatted_json, send_response_dict

    except Exception as e:
        print("Error in format_afd_item_json-",e)
        send_response_dict['responseStatus'] = 'FAILED'
        send_response_dict['responseData'] = 'Error in format_afd_item_json - {}'.format(e)
        return 'FAILED', send_response_dict

def format_afd_item_envid_json(create_m2_env_response, afd_item):
    try:
        send_response_dict = {'responseStatus': 'FAILED', 'responseData': 'FAILED'}
        formatted_json = afd_item
        formatted_json['FeatureParams']['pM2EnvId']['Default'] = create_m2_env_response['environmentId']

        send_response_dict['responseStatus'] = 'SUCCESS'
        send_response_dict['responseData'] = 'format_afd_item_envid_json'
        return formatted_json, send_response_dict

    except Exception as e:
        print("Error in format_afd_item_envid_json-",e)
        send_response_dict['responseStatus'] = 'FAILED'
        send_response_dict['responseData'] = 'Error in format_afd_item_envid_json - {}'.format(e)
        return 'FAILED', send_response_dict

def format_afd_item_efsid_json(FsId, afd_item):
    try:
        send_response_dict = {'responseStatus': 'FAILED', 'responseData': 'FAILED'}
        print("FsId in format_afd_item_efsid_json is ", FsId)
        formatted_json = afd_item
        formatted_json['FeatureParams']['pEfsId']['Default'] = FsId
        print("formatted_json['FeatureParams']['pEfsId']['Default'] is ", formatted_json['FeatureParams']['pEfsId']['Default'])

        send_response_dict['responseStatus'] = 'SUCCESS'
        send_response_dict['responseData'] = 'format_afd_item_efsid_json'
        return formatted_json, send_response_dict

    except Exception as e:
        print("Error in format_afd_item_efsid_json-",e)
        send_response_dict['responseStatus'] = 'FAILED'
        send_response_dict['responseData'] = 'Error in format_afd_item_efsid_json - {}'.format(e)
        return 'FAILED', send_response_dict

def put_afd_item(dynamodb_resource, target_table, obj_json):
    try:
        send_response_dict = {'responseStatus': 'FAILED', 'responseData': 'FAILED'}
        table = dynamodb_resource.Table(target_table)
        put_afd_item_response = table.put_item(Item=obj_json)

        HttpStatus = put_afd_item_response['ResponseMetadata']['HTTPStatusCode']
        if HttpStatus == 200 or HttpStatus == 202:
            send_response_dict['responseStatus'] = 'SUCCESS'
            send_response_dict['responseData'] = 'put_afd_item'
        else:
            send_response_dict['responseStatus'] = 'FAILED'
            send_response_dict['responseData'] = 'Error in put_afd_item'
        return send_response_dict

    except Exception as e:
        print("Error in put_afd_item-",e)
        send_response_dict['responseStatus'] = 'FAILED'
        send_response_dict['responseData'] = 'Error in put_afd_item - {}'.format(e)
        return 'FAILED', send_response_dict

    except boto3.exceptions.botocore.client.ClientError as e:
        print("Error adding item: {}  - {}".format(obj_json, str(e)))
        send_response_dict['responseStatus'] = 'FAILED'
        send_response_dict['responseData'] = 'Error in put_afd_item - {}'.format(e)
        return 'FAILED', send_response_dict

def update_m2_env(mainframe_client, final_db_params_dict):
    try:
        send_response_dict = {'responseStatus': 'FAILED', 'responseData': 'FAILED'}
        M2EnvId = final_db_params_dict['pM2EnvId']['Default']
        HighAvailabilityConfig = int(final_db_params_dict['pHighAvailabilityConfig']['Default'])
        UpdateEnvEngVer = final_db_params_dict['pUpdateEnvEngVer']['Default']
        InstanceType = final_db_params_dict['pInstanceType']['Default']
        UpdateInstanceTypeFlag = final_db_params_dict['pUpdateInstanceTypeFlag']['Default']
        UpdateEngineVersionFlag = final_db_params_dict['pUpdateEngineVersionFlag']['Default']
        UpdateDesiredCapacityFlag = final_db_params_dict['pUpdateDesiredCapacityFlag']['Default']
        UpdatePrefMaintWinFlag = final_db_params_dict['pUpdatePrefMaintWinFlag']['Default']
        print("UpdateInstanceTypeFlag is ", UpdateInstanceTypeFlag)
        print("UpdateEngineVersionFlag is ", UpdateEngineVersionFlag)
        print("UpdateDesiredCapacityFlag is ", UpdateDesiredCapacityFlag)
        print("UpdatePrefMaintWinFlag is ", UpdatePrefMaintWinFlag)

        # desired maintenance window format: 'wed:03:27-wed:05:27'
        PrefMaintWinDay = final_db_params_dict['pPrefMaintWinDay']['Default']
        PrefMaintWinHrStart = final_db_params_dict['pPrefMaintWinHrStart']['Default']
        PrefMaintWinHrStop = final_db_params_dict['pPrefMaintWinHrStop']['Default']
        PrefMaintWinMin = final_db_params_dict['pPrefMaintWinMin']['Default']
        maint_window = PrefMaintWinDay+':'+PrefMaintWinHrStart+':'+PrefMaintWinMin+'-'+PrefMaintWinDay+':'+PrefMaintWinHrStop+':'+PrefMaintWinMin
        print("maint_window is ", maint_window)

        # WARNINGS
        #    Only one setting may be updated at a time
        #    Current AWS maintenance window requirements are:
        #        Engine version update MUST be applied with maintenance window True
        #        All other updates MUST be applied with maintenance window False
        #        https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/m2.html#MainframeModernization.Client.update_environment

        if UpdateInstanceTypeFlag:
            print("processing UpdateInstanceType")
            update_env_response = mainframe_client.update_environment(
                environmentId=M2EnvId,
                applyDuringMaintenanceWindow=False,
                instanceType=InstanceType
            )
        elif UpdateDesiredCapacityFlag:
            print("processing UpdateDesiredCapacity")
            update_env_response = mainframe_client.update_environment(
                environmentId=M2EnvId,
                applyDuringMaintenanceWindow=False,
                desiredCapacity=HighAvailabilityConfig
            )
        elif UpdatePrefMaintWinFlag:
            print("processing UpdatePrefMaintWin")
            update_env_response = mainframe_client.update_environment(
                environmentId=M2EnvId,
                applyDuringMaintenanceWindow=False,
                preferredMaintenanceWindow=maint_window
            )
        elif UpdateEngineVersionFlag:
            print("processing UpdateEngineVersion")
            update_env_response = mainframe_client.update_environment(
                environmentId=M2EnvId,
                applyDuringMaintenanceWindow=True,
                engineVersion=UpdateEnvEngVer
            )
        else:
            print("no update Flag condition met")
            send_response_dict['responseStatus'] = 'FAILED'
            send_response_dict['responseData'] = 'Error in update_m2_env, no Flag condition met'
            return update_env_response, send_response_dict

        print("update_env_response in update_m2_env is ", update_env_response)
        HttpStatus = update_env_response['ResponseMetadata']['HTTPStatusCode']
        if HttpStatus == 200 or HttpStatus == 202:
            send_response_dict['responseStatus'] = 'SUCCESS'
            send_response_dict['responseData'] = 'update_m2_env'
        else:
            send_response_dict['responseStatus'] = 'FAILED'
            send_response_dict['responseData'] = 'Error in update_m2_env'
        return update_env_response, send_response_dict

    except Exception as e:
        print("Error in update_m2_env-",e)
        send_response_dict['responseStatus'] = 'FAILED'
        send_response_dict['responseData'] = 'Error in update_m2_env - {}'.format(e)
        return 'FAILED', send_response_dict

    except boto3.exceptions.botocore.client.ClientError as e:
        print("Client Error in update_m2_env : {}  - {}".format(obj_json, str(e)))
        send_response_dict['responseStatus'] = 'FAILED'
        send_response_dict['responseData'] = 'Error in update_m2_env - {}'.format(e)
        return 'FAILED', send_response_dict



def lambda_handler(event, context):
    print('Event Received - ',event)
    print('Context Received - ',context)
    request_type = event['RequestType']

    lambda_result = None

    ###  process Delete event
    if request_type in ['Delete'] and ('ServiceToken' in event):
        print("Processing Delete event in lambda_handler")
        return(send_response(event, context, 'SUCCESS', 'lambda_handler processing Delete event',None, None, 'lambda_handler processing Delete event'))


    ###  process Create event
    if request_type in ['Create'] and ('ServiceToken' in event):
        try:
            #send_response(event, context, 'SUCCESS', 'Delete event received')

            ### read parameters from Account Feature Definition table to check pFindSubnets

            initial_db_params_dict, send_response_dict, afd_item = get_afd_params(dynamodb_resource, target_table, feature_name)
            print(" ")
            print("initial_db_params_dict is ", initial_db_params_dict)

            ### If pFindSubnets is true then locate Workload VPC private subnets and security group and update Account Feature Definition table

            if initial_db_params_dict['pFindSubnets']['Default']:
                work_priv_subnet_list, subnets_response, send_response_dict = get_workloadvpc_priv_subnets(ec2_client)
                if send_response_dict['responseStatus'] == 'FAILED':
                    return(send_response(event, context, send_response_dict['responseStatus'], send_response_dict['responseData'],None, None, send_response_dict['responseData']))
                print("work_priv_subnet_list is ", work_priv_subnet_list)
                wvpc_default_sg, send_response_dict = get_sg(ec2_client, subnets_response)
                if send_response_dict['responseStatus'] == 'FAILED':
                    return(send_response(event, context, send_response_dict['responseStatus'], send_response_dict['responseData']))
                print("wvpc_default_sg is ", wvpc_default_sg)

                ### write the list work_priv_subnet_list and SG wvpc_default_sg to the db

                # format the DB item
                obj_json, send_response_dict = format_afd_item_json(work_priv_subnet_list, wvpc_default_sg, afd_item)
                print("obj_json is ", obj_json)
                if send_response_dict['responseStatus'] == 'FAILED':
                    return(send_response(event, context, send_response_dict['responseStatus'], send_response_dict['responseData'],None, None, send_response_dict['responseData']))

                # write to the DB
                send_response_dict = put_afd_item(dynamodb_resource, target_table, obj_json)
                print("put_afd_item status is ", send_response_dict['responseStatus'])
                if send_response_dict['responseStatus'] == 'FAILED':
                    return(send_response(event, context, send_response_dict['responseStatus'], send_response_dict['responseData'],None, None, send_response_dict['responseData']))

            ### read parameters from Account Feature Definition table for creating M2 environment

            final_db_params_dict, send_response_dict, afd_item = get_afd_params(dynamodb_resource, target_table, feature_name)
            if send_response_dict['responseStatus'] == 'FAILED':
                return(send_response(event, context, send_response_dict['responseStatus'], send_response_dict['responseData'],None, None, send_response_dict['responseData']))
            print("final_db_params_dict is ", final_db_params_dict)

            ### Create EFS if user does not have one

            pCreateEfs = final_db_params_dict['pCreateEfs']['Default']
            if pCreateEfs:
                # if pCreateEFS is False then this section is skipped and pEfsId must be populated by user before deployment
                print('pCreateEfs is {} creating EFS'.format(pCreateEfs))
                create_efs_result, send_response_dict = create_efs(final_db_params_dict, efs_client)
                print("create_efs_result in lambda handler is ", create_efs_result)
                if 'fs-' in create_efs_result:
                    FsId = create_efs_result
                else:
                    print("No FS Id to pass to create_m2_env")
                    return(send_response(event, context, 'FAILED', 'FAILED',None, None, 'FS ID not returned'))

                ### add EFS Id to the DB

                # read the current item
                initial_db_params_dict, send_response_dict, afd_item = get_afd_params(dynamodb_resource, target_table, feature_name)

                # format the payload to be sent to the DB
                obj_json, send_response_dict = format_afd_item_efsid_json(FsId, afd_item)
                print("obj_json for adding Env Id is ", obj_json)
                if send_response_dict['responseStatus'] == 'FAILED':
                    return(send_response(event, context, send_response_dict['responseStatus'], send_response_dict['responseData'],None, None, send_response_dict['responseData']))

                # write to the DB
                send_response_dict = put_afd_item(dynamodb_resource, target_table, obj_json)
                print("put_afd_item status is ", send_response_dict['responseStatus'])
                if send_response_dict['responseStatus'] == 'FAILED':
                    return(send_response(event, context, send_response_dict['responseStatus'], send_response_dict['responseData'],None, None, send_response_dict['responseData']))
            else:
                print('pCreateEfs is {} using Customer Provided EFS in pEfsId instead'.format(pCreateEfs))


            ### Create M2 environment

            if not pCreateEfs:
                print('pCreateEFS is {} so EFS already exists, reading the EfsId from the DB'.format(pCreateEfs))
                initial_db_params_dict, send_response_dict, afd_item = get_afd_params(dynamodb_resource, target_table, feature_name)
                FsId = initial_db_params_dict['pEfsId']['Default']
                print("Customer provided EFS Id is ", FsId)
                if FsId == 'Dummy':
                    print("pCreateEFS is False and pEfsId was not manually updated in the database, aborting M2 creation")
                    return(send_response(event, context, 'FAILED', 'pEfsId not updated in DB',None, None, 'pEfsId not updated in DB'))
            else:
                print("using newly created EfsId")

            create_m2_env_response, send_response_dict = create_m2_env(mainframe_client, final_db_params_dict, FsId)
            print("create_m2_env_response is ", create_m2_env_response)
            print("send_response_dict in lambda for create_m2_env is ", send_response_dict)
            if send_response_dict['responseStatus'] == 'FAILED':
                return(send_response(event, context, send_response_dict['responseStatus'], send_response_dict['responseData'],None, None, send_response_dict['responseData']))

            ### add M2 Environment Id to the DB

            # read the current item
            initial_db_params_dict, send_response_dict, afd_item = get_afd_params(dynamodb_resource, target_table, feature_name)

            # format the DB item
            obj_json, send_response_dict = format_afd_item_envid_json(create_m2_env_response, afd_item)
            print("obj_json for adding Env Id is ", obj_json)
            if send_response_dict['responseStatus'] == 'FAILED':
                return(send_response(event, context, send_response_dict['responseStatus'], send_response_dict['responseData'],None, None, send_response_dict['responseData']))

            # write to the DB
            send_response_dict = put_afd_item(dynamodb_resource, target_table, obj_json)
            print("put_afd_item status is ", send_response_dict['responseStatus'])
            if send_response_dict['responseStatus'] == 'FAILED':
                return(send_response(event, context, send_response_dict['responseStatus'], send_response_dict['responseData'],None, None, send_response_dict['responseData']))

        except Exception as e:
            print('Error - ',e)
            send_response(event, context, 'FAILED', 'Error in Create event')

    ###  process stack Update event for M2

    #if request_type in ['Update'] and ('ServiceToken' in event):
    if event['RequestType'] == 'Update':
        try:

            ### read parameters from Account Feature Definition table for creating M2 environment
            final_db_params_dict, send_response_dict, afd_item = get_afd_params(dynamodb_resource, target_table, feature_name)
            if send_response_dict['responseStatus'] == 'FAILED':
                return(send_response(event, context, send_response_dict['responseStatus'], send_response_dict['responseData'],None, None, send_response_dict['responseData']))
            print("final_db_params_dict is ", final_db_params_dict)


            ### update M2 environment
            update_m2_env_response, send_response_dict = update_m2_env(mainframe_client, final_db_params_dict)
            if send_response_dict['responseStatus'] == 'FAILED':
                return(send_response(event, context, send_response_dict['responseStatus'], send_response_dict['responseData'],None, None, send_response_dict['responseData']))
            print("update_m2_env_response is ", update_m2_env_response)

        except Exception as e:
            print('Error - ',e)
            send_response(event, context, 'FAILED', 'Error in Update event')



    ### End lambda, send final status to the stack
    # Hard coding SUCCESS will falsely set stack creation to success even if the lambda does not run correctly.  To correct, need to return and process failures from the functions.
    print("end of lambda handler")
    print("send_response_dict['responseStatus'] is ", send_response_dict['responseStatus'])
    print("send_response_dict['responseData'] is ", send_response_dict['responseData'])
    send_response(event, context, send_response_dict['responseStatus'], send_response_dict['responseData'])
