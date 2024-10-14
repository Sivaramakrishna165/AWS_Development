import json
import boto3
import os
from botocore.config import Config
import http.client
import urllib.parse
from uuid import uuid4
from time import sleep


def get_db_items(client,item_name):
    try:
        response = client.get_item(Key={"Feature":item_name})
        return response['Item']
    except Exception as e:
        print("Error-get_db_items()",e)
        
def get_db_instance(client):
    try:
        response = client.describe_db_instances()
        return response['DBInstances']
    except Exception as e:
        print("Error-get_db_instance()",e)

def enable_backup_replication(client,source_region,instance_arn):
    try:
        response = client.start_db_instance_automated_backups_replication(SourceDBInstanceArn=instance_arn,BackupRetentionPeriod=35,SourceRegion=source_region)
        return True
    except Exception as e:
        print("Error-enable_backup_replication()",e)
        return False
        
def get_private_subnets(client,vpc_id):
    try:
        primary_subnets=[]
        resp_subnets = client.describe_subnets(
                                        Filters=[
                                            {
                                                'Name': 'vpc-id',
                                                'Values': [
                                                    vpc_id,
                                                ]
                                            },
                                        ],
                                    )
        for subnet in resp_subnets['Subnets']:
         
            resp_rt = client.describe_route_tables(
                Filters=[
                    {
                        'Name': 'association.subnet-id',
                        'Values': [
                            subnet['SubnetId'],
                        ]
                    },
                ],
            )
            
            for rt in resp_rt['RouteTables']:
                routes = [obj for obj in rt['Routes'] if 'GatewayId' in obj and 'igw' in obj['GatewayId']]
                if(not routes): # If IGW is not there in routes then it is a Private subnet
                    if(subnet['SubnetId'] not in primary_subnets):
                        primary_subnets.append(subnet['SubnetId'])
                        
        return primary_subnets
    except Exception as e:
        print("ERROR-get_private_subnets()",e)
        
def create_db_subnet(client,subnets,tags,group_name,description):
    try:
        response = client.create_db_subnet_group(DBSubnetGroupName=group_name, DBSubnetGroupDescription=description, SubnetIds=subnets, Tags=tags)
    except Exception as e:
        print("Subnet group for RDS already present",e)

def create_security_group(client,source_sg,vpc_id,group_name):
    try:
        try:
            response = client.create_security_group(
            Description="DB Security group for rds",
            GroupName=group_name,
            VpcId=vpc_id,
            
            )
            sg_id=response['GroupId']
            
            
        except:
            response = client.describe_security_groups( Filters=[{'Name': 'group-name','Values': [group_name]}])
            sg_id=[resp['GroupId'] for resp in response['SecurityGroups']][0]
        
    
        try:
            response = client.authorize_security_group_ingress(GroupId=sg_id,IpPermissions=[{'FromPort': 3306,'IpProtocol': 'tcp','ToPort': 3306,'UserIdGroupPairs': [{'GroupId': sg_id}]}])
        except:
            print("Already inboud rule for rds is present for security group: {}".format(sg_id))
        return sg_id
    except Exception as e:
        print("Error-create_security_group()",e)
        
        
def create_pitr_rds(client,db_identifier,db_instance_class,subnets,db_multi_az,db_name,db_option_gp_name,sg_id,db_iam_authentication,db_cw_logs,db_parameter_group,secondary_backup_arn,db_allocatedstorage,tags,storage_type):
    try:
        if db_multi_az.lower()=="false":
            db_multi_az=False
        else:
            db_multi_az=True
        if db_iam_authentication.lower()=="false":
            db_iam_authentication=False
        else:
            db_iam_authentication=True
            
        if db_parameter_group=="" and db_option_gp_name=="":
            response = client.restore_db_instance_to_point_in_time(
            TargetDBInstanceIdentifier=db_identifier.lower(),
            UseLatestRestorableTime=True,
            DBInstanceClass=db_instance_class,
            Port=3306,
            DBSubnetGroupName=subnets,
            MultiAZ=db_multi_az,
            #DBName=db_name,
            Engine="postgresql",
            Tags=tags,
            StorageType=storage_type,
            
            VpcSecurityGroupIds=sg_id,
            
            EnableIAMDatabaseAuthentication=db_iam_authentication,
            EnableCloudwatchLogsExports=db_cw_logs.split(","),
            
            
            #SourceDbiResourceId=dbi_id,
            SourceDBInstanceAutomatedBackupsArn=secondary_backup_arn,
            AllocatedStorage=db_allocatedstorage
            )
            return None
        
        if db_parameter_group=="":
            response = client.restore_db_instance_to_point_in_time(
            TargetDBInstanceIdentifier=db_identifier.lower(),
            UseLatestRestorableTime=True,
            DBInstanceClass=db_instance_class,
            Port=3306,
            DBSubnetGroupName=subnets,
            MultiAZ=db_multi_az,
            #DBName=db_name,
            Engine="postgresql",
            OptionGroupName=db_option_gp_name,
            Tags=tags,
            StorageType=storage_type,
            
            VpcSecurityGroupIds=sg_id,
            
            EnableIAMDatabaseAuthentication=db_iam_authentication,
            EnableCloudwatchLogsExports=db_cw_logs.split(","),
            
            
            #SourceDbiResourceId=dbi_id,
            SourceDBInstanceAutomatedBackupsArn=secondary_backup_arn,
            AllocatedStorage=db_allocatedstorage
            )
            return None
            
        if db_option_gp_name=="":
            response = client.restore_db_instance_to_point_in_time(
            TargetDBInstanceIdentifier=db_identifier.lower(),
            UseLatestRestorableTime=True,
            DBInstanceClass=db_instance_class,
            Port=3306,
            DBSubnetGroupName=subnets,
            MultiAZ=db_multi_az,
            #DBName=db_name,
            Engine="postgresql",
            Tags=tags,
            StorageType=storage_type,
            
            VpcSecurityGroupIds=sg_id,
            
            EnableIAMDatabaseAuthentication=db_iam_authentication,
            EnableCloudwatchLogsExports=db_cw_logs.split(","),
            DBParameterGroupName=db_parameter_group,
            
            
            #SourceDbiResourceId=dbi_id,
            SourceDBInstanceAutomatedBackupsArn=secondary_backup_arn,
            AllocatedStorage=db_allocatedstorage
            )
            return None
        
        response = client.restore_db_instance_to_point_in_time(
            TargetDBInstanceIdentifier=db_identifier.lower(),
            UseLatestRestorableTime=True,
            DBInstanceClass=db_instance_class,
            Port=3306,
            DBSubnetGroupName=subnets,
            MultiAZ=db_multi_az,
            #DBName=db_name,
            Engine="postgresql",
            OptionGroupName=db_option_gp_name,
            Tags=tags,
            StorageType=storage_type,
            
            VpcSecurityGroupIds=sg_id,
            
            EnableIAMDatabaseAuthentication=db_iam_authentication,
            EnableCloudwatchLogsExports=db_cw_logs.split(","),
            DBParameterGroupName=db_parameter_group,
            
            
            #SourceDbiResourceId=dbi_id,
            SourceDBInstanceAutomatedBackupsArn=secondary_backup_arn,
            AllocatedStorage=db_allocatedstorage
        )
    except Exception as e:
        print("Error-create_pitr_rds()",e)
        exit()

def get_automated_backup(client,db_identifier):
    try:
        paginator = client.get_paginator('describe_db_instance_automated_backups')
        response_iterator = paginator.paginate()
        for response in response_iterator:
            for resp in response['DBInstanceAutomatedBackups']:
                if resp['DBInstanceIdentifier']==db_identifier.lower():
                    return resp['DBInstanceAutomatedBackupsArn']
        
                
        print("There are no automated backup for the resource")
        return None
    except Exception as e:
        print("Error-get_automated_backup()",e)

def disable_event_bridge_rule(client,event_rule):
    try:
        response = client.disable_rule(Name=event_rule)
    except Exception as e:
        print("Error-disable_event_bridge_rule()",e)
        
def enable_event_bridge_rule(client,event_rule):
    try:
        response = client.enable_rule(Name=event_rule)

    except Exception as e:
        print("Error-enable_event_bridge_rule()",e)
        
        
def update_rule(client,rule, target_arn,input_json,rule_id):
    try:
        response = client.put_targets( Rule=rule,Targets=[ { 'Id': rule_id,'Arn': target_arn,'Input': input_json}])
    except Exception as e:
        print("Error-update_rule()",e)
        
def create_alarms(client,feature_name,alarm_name,sns_topic,statistics,db_identifier,periods,evaluation_period,threshold,comp_oper):
    try:
        response = client.put_metric_alarm(AlarmName=feature_name+"-"+alarm_name+"-"+db_identifier.lower(),AlarmActions=[sns_topic],MetricName=alarm_name.replace("Database","").replace("Alarm",""),Namespace="AWS/RDS",Statistic=statistics,Dimensions=[{'Name': 'DBInstanceIdentifier','Value': db_identifier.lower()}],Period=int(periods), EvaluationPeriods=int(evaluation_period), Threshold=float(threshold), ComparisonOperator=comp_oper,TreatMissingData="missing")
    except Exception as e:
        print("Error-create_alarms()",e)
        
def create_event_subscription(client,subscription,db_identifier,sns_topic,tags):
    try:
        response = client.create_event_subscription(SubscriptionName=subscription,SnsTopicArn=sns_topic,SourceType='db-instance',EventCategories=["failover","failure", "low storage", "maintenance", "read replica", "recovery"],SourceIds=[db_identifier.lower()],Enabled=True,Tags=tags)

    except Exception as e:
        print("Error-create_event_subscription()",e)

def delete_rds_instance(client,db_identifier):
    try:
        response = client.delete_db_instance(DBInstanceIdentifier=db_identifier.lower(), SkipFinalSnapshot=True, DeleteAutomatedBackups=True)
    except Exception as e:
        print("Error-delete_rds_instance",e)
    
def get_stack_resource(client,stack_name,logical_name):
    try:
        response = client.describe_stack_resources(
        StackName=stack_name,
        LogicalResourceId=logical_name
        )
        
        return response['StackResources'][0]['PhysicalResourceId']
    except Exception as e:
        print("Error-get_stack_resource",e)    
        
def delete_alarms(client,alarms):
    try:
        response = client.delete_alarms(AlarmNames=alarms)
        
    except Exception as e:
        print("Error-delete_alarms()",e)

def delete_event_subscription(client,event_subscription):
    try:
        response = client.delete_event_subscription(SubscriptionName=event_subscription)
    except Exception as e:
        print("Error-delete_event_subscription()",e)

def get_alarms(client, alarms):
    try:
        response = client.describe_alarms(AlarmNames=alarms)
        return response['MetricAlarms']
    except Exception as e:
        print("Error-get_alarms()",e)

def get_subscriptions(client, event_subscription):
    try:
        response = client.describe_event_subscriptions(SubscriptionName=event_subscription)
        return response['EventSubscriptionsList']
    except Exception as e:
        pass
        #print("Error-get_subscriptions()",e)
    
def invoke_lambda(client,function,payload):
    try:
        response = client.invoke(FunctionName=function,InvocationType='Event',Payload=bytes(json.dumps(payload), encoding='utf8'))
    except Exception as e:
        print("Error-invoke_lambda()",e)
def update_parameter(client,param,msg):
    try:
        response = client.put_parameter(Name=param,Value=msg,Type='String',Overwrite=True)
    except Exception as e:
        print("Error-update_parameter()",e)
def get_parameter(client, ssm_param):
    try:
        response = client.get_parameter(Name=ssm_param)
        return response['Parameter']['Value']
    except Exception as e:
        print("Error-get_parameter()",e)

#def update_rds_instance(secondary_rds_client,secondary_db_identifier,db_option_gp_name,db_parameter_group,db_instance_class,db_cw_logs,db_allocatedstorage,db_iam_authentication,primary_sns_topic):



def send_response(request, response, status=None, reason=None):
    try:
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
    except Exception as e:
        print("Error-send_response()",e)


def lambda_handler(event, context):
    try:
        print("Received Event-",event)

        primary_region=os.environ["PRIMARY_REGION"]
        secondary_region=os.environ["AWS_REGION"]
        seconary_region_resources=os.environ["SECONDARY_REGION_RESOURCES"]
        feature_name=os.environ["FEATURE_NAME"]
        secondary_sns_topic=os.environ["SECONDARY_SNS_TOPIC"]
        ssm_param=os.environ["SSM_PARAM"]
        alarm_ssm_param=os.environ["ALARMS_SSM_PARAM"]
        
        secondary_stack_name=seconary_region_resources
        rule_name_logical_name="rDxcmsTriggerFailoverEventsRule"

        
        create_incident_lambda_arn=os.environ["CREATE_INCIDENT_LAMBDA"]
        table_name="AccountFeatureDefinitions"
        
        config=Config(retries=dict(max_attempts=10,mode='standard'))
        primary_dynamodb = boto3.resource('dynamodb',region_name=primary_region,config=config)
        table = primary_dynamodb.Table(table_name)
        primary_rds_client= boto3.client('rds',region_name=primary_region,config=config)
        primary_cf_client= boto3.client('cloudformation',region_name=primary_region,config=config)
        secondary_cf_client= boto3.client('cloudformation',region_name=secondary_region,config=config)
        secondary_event_bridge_client = boto3.client('events',region_name=secondary_region,config=config)
        secondary_lambda_client=boto3.client('lambda',region_name=secondary_region,config=config)
        
        primary_cw_client=boto3.client('cloudwatch',region_name=primary_region,config=config)
        
        rule_name=get_stack_resource(secondary_cf_client,secondary_stack_name,rule_name_logical_name)

        tags=[{'Key': 'Owner','Value': 'DXC'},{'Key': 'Application','Value': 'AWS Managed Services'}]
        secondary_DBSubnetGroupName="Feature-RDSInstancePostgresql-Multi-Region-"+str(uuid4())
        secondary_DBSubnetGroupDescription="RDSInstancePostgresql-Multi-Region"
        secondary_sg_group_name="DB Security group for rds-"+str(uuid4())
        primary_sg_logical_name="DatabaseSecurityGroup"
        primary_subnet_gp_logical_name="DBSubnetGroup"
        primary_nested_stack_logical_id="RDSInstancePostgresql"
        try:
            item=get_db_items(table, feature_name)
            secondary_db_identifier=item['RDSParameters']['SecondaryDBInstanceIdentifier']['Default'].lower()
            alarms_params=item["Alarms"]
            rds_params=item['RDSParameters']
                
            secondary_vpc_id=rds_params["SecondaryRegionVpcName"]['Default']
            secondary_source_sg=rds_params["SecondaryRegionSecurityGroup"]['Default']
            db_identifier=item['RDSParameters']['DBInstanceIdentifier']['Default'].lower()
            db_option_gp_name=item['RDSParameters']['DBOptionGroupName']['Default']
            db_engine_version=item['RDSParameters']['EngineVersion']['Default']
            db_sub_domain_name=item['RDSParameters']['SubDomainNameWithDot']['Default']
            db_instance_class=item['RDSParameters']['DBInstanceClass']['Default']
            db_password=item['RDSParameters']['DBMasterUserPassword']['Default']
            db_username=item['RDSParameters']['DBMasterUsername']['Default']
            db_maintainance_window=item['RDSParameters']['PreferredMaintenanceWindow']['Default']
            db_cw_logs=item['RDSParameters']['CloudwatchLogsExports']['Default']
            db_backup_window=item['RDSParameters']['PreferredBackupWindow']['Default']
            db_parameter_group=item['RDSParameters']['DBParameterGroupName']['Default']
            db_backup_retention=item['RDSParameters']['DBBackupRetentionPeriod']['Default']
            db_allocatedstorage=item['RDSParameters']['DBAllocatedStorage']['Default']
            db_name=item['RDSParameters']['DBName']['Default']
            db_iam_authentication=item['RDSParameters']['EnableIAMDatabaseAuthentication']['Default']
            db_multi_az=item['RDSParameters']['DBMultiAZ']['Default']
            primary_sns_topic=item['RDSParameters']['PriorityIncidentTopic']['Default']
            storage_type=item['RDSParameters']['StorageType']['Default']
            
            feature_stack="Feature"+item["Feature"]+"Stack"
        except Exception as e:
            print("Error-getting table items-",e)
        
        secondary_rds_client= boto3.client('rds',region_name=secondary_region,config=config)
        secondary_ec2_client=boto3.client('ec2',region_name=secondary_region,config=config)
        secondary_event_bridge_client = boto3.client('events',region_name=secondary_region,config=config)
        secondary_cw_client=boto3.client('cloudwatch',region_name=secondary_region,config=config)
        secondary_ssm_client=boto3.client('ssm',region_name=secondary_region,config=config)
        
        response={}
        if "RequestType" in event:
            if (event['RequestType'] in ['Create','Update','Delete']) and ('ServiceToken' in event):            
                response['Status'] = 'SUCCESS'
                response['Reason'] = 'See the details in CloudWatch Log Stream: ' + context.log_stream_name
                response['PhysicalResourceId'] = context.log_stream_name
                response['StackId'] = event['StackId']
                response['RequestId'] = event['RequestId']
                response['LogicalResourceId'] = event['LogicalResourceId']
                response['NoEcho'] = False
                response['Data'] = {}
            if event['RequestType'] in ['Delete','Update']:
                send_response(event, response, status='SUCCESS', reason='Delete event received')
            
            if 'ResourceProperties' in event:
                if "create" in event['ResourceProperties']: 
                    rds_params=item['RDSParameters']
                    ssm_db_item={"secondary_vpc_id":secondary_vpc_id,
                                 "secondary_source_sg":secondary_source_sg,
                                 "db_identifier":db_identifier.lower(),
                                 "db_option_gp_name":db_option_gp_name,
                                 "db_instance_class":db_instance_class,
                                 "db_cw_logs":db_cw_logs,
                                 "db_parameter_group":db_parameter_group,
                                 "db_allocatedstorage":str(db_allocatedstorage),
                                 "db_iam_authentication":db_iam_authentication,
                                 "db_name":db_name,
                                 "db_multi_az":db_multi_az,
                                 "primary_sns_topic":primary_sns_topic,
                                 "secondary_db_identifier":secondary_db_identifier.lower(),
                                 "storage_type":storage_type}
                    alarm_ssm={
                                 "alarms":item["Alarms"]}
                    for alarm in alarm_ssm["alarms"].keys():
                        for item_param in alarm_ssm["alarms"][alarm].keys():
                            if 'AllowedValues' in alarm_ssm["alarms"][alarm][item_param]:
                                alarm_ssm["alarms"][alarm][item_param].pop("AllowedValues")
                            if "Description" in alarm_ssm["alarms"][alarm][item_param]:
                                alarm_ssm["alarms"][alarm][item_param].pop("Description")
                            if "Type" in alarm_ssm["alarms"][alarm][item_param]:
                                alarm_ssm["alarms"][alarm][item_param].pop("Type")
                            if 'Default' in alarm_ssm["alarms"][alarm][item_param]:
                                alarm_ssm["alarms"][alarm][item_param]['Default']=str(alarm_ssm["alarms"][alarm][item_param]['Default'])
                            if 'MinValue' in alarm_ssm["alarms"][alarm][item_param]:
                                alarm_ssm["alarms"][alarm][item_param].pop("MinValue")
                            if 'MaxValue' in alarm_ssm["alarms"][alarm][item_param]:
                                alarm_ssm["alarms"][alarm][item_param].pop("MaxValue")
                    update_parameter(secondary_ssm_client,ssm_param,str(ssm_db_item))
                    update_parameter(secondary_ssm_client,alarm_ssm_param,str(alarm_ssm))
                    secondary_vpc_id=rds_params["SecondaryRegionVpcName"]['Default']
                    secondary_source_sg=rds_params["SecondaryRegionSecurityGroup"]['Default']
                    
                    if secondary_vpc_id=="" or secondary_source_sg=="":
                        print("Please fill 'SecondaryRegionVpcName' and 'SecondaryRegionSecurityGroup' in account feature defintion table.")
                        exit()
                    
                    db_instances=get_db_instance(primary_rds_client)
                    if any(db['DBInstanceIdentifier']==db_identifier.lower() for db in db_instances):
                        print("DB instance present with name: {}".format(db_identifier.lower()))
                        
                        if enable_backup_replication(secondary_rds_client,primary_region,"arn:aws:rds:"+primary_region+":"+str(context.invoked_function_arn.split(":")[4])+":db:"+db_identifier):
                            print("Automated backup replication successful for region: {}".format(secondary_region))
                        else:
                            print("Unable to enable Automated backup replication in secondary region!!")
                            send_response(event, response, status='FAILED', reason="Unable to enable Automated backup replication in secondary region!!")
                            raise "Failed to enable Automated backup replication"
                    else:
                        print("Primary RDS instance not present")
                        send_response(event, response, status='FAILED', reason="Unable to enable Automated backup replication in secondary region!!")
                        raise "Primary RDS instance not present"
                    
                    sleep(380)
                    send_response(event, response, status='SUCCESS', reason='Lambda Invoked')
 
        if "detail" in event:
            if event["detail"]["eventTypeCategory"].lower()=="issue" and event["detail"]["statusCode"].lower()=="open":
                automated_backup_arn=get_automated_backup(secondary_rds_client,db_identifier.lower())
                if not automated_backup_arn:
                    print("Automated backup not available for the DB instance: {}".format(db_identifier.lower()))
                    exit()
                
                sleep(360)
                ssm_param_value=json.loads(str(get_parameter(secondary_ssm_client,ssm_param)).replace("'",'"'))
                alarms_params_value=json.loads(str(get_parameter(secondary_ssm_client,alarm_ssm_param)).replace("'",'"'))
                secondary_vpc_id=ssm_param_value["secondary_vpc_id"]
                secondary_source_sg=ssm_param_value["secondary_source_sg"]
                db_identifier=ssm_param_value["db_identifier"].lower()
                db_option_gp_name=ssm_param_value["db_option_gp_name"]
                db_instance_class=ssm_param_value["db_instance_class"]
                db_cw_logs=ssm_param_value["db_cw_logs"]
                db_parameter_group=ssm_param_value["db_parameter_group"]
                db_allocatedstorage=ssm_param_value["db_allocatedstorage"]
                db_iam_authentication=ssm_param_value["db_iam_authentication"]
                db_name=ssm_param_value["db_name"]
                db_multi_az=ssm_param_value["db_multi_az"]
                primary_sns_topic=ssm_param_value["primary_sns_topic"]
                secondary_db_identifier=ssm_param_value["secondary_db_identifier"].lower()
                storage_type=ssm_param_value["storage_type"]
                                 
                subnets=get_private_subnets(secondary_ec2_client,secondary_vpc_id)
                sg_id=create_security_group(secondary_ec2_client,secondary_source_sg,secondary_vpc_id,secondary_sg_group_name)
                create_db_subnet(secondary_rds_client,subnets,tags,secondary_DBSubnetGroupName,secondary_DBSubnetGroupDescription)
                print("Created subnet group and security group in secondary region")
                

                create_pitr_rds(secondary_rds_client,secondary_db_identifier,db_instance_class,secondary_DBSubnetGroupName,db_multi_az,db_name,db_option_gp_name,[sg_id],db_iam_authentication,db_cw_logs,db_parameter_group,automated_backup_arn,int(db_allocatedstorage),tags,storage_type)
                print("RDS instance creating successfully in secondary region")
                
                alarms_params=alarms_params_value["alarms"]
                for alarm in alarms_params.keys():
                    alarm_metric=alarm.replace("Database","").replace("Alarm","")
                    if alarms_params[alarm]["Apply"+alarm_metric+"Alarm"]:
                        
                        periods=int(alarms_params[alarm][alarm_metric+"Period"]["Default"])
                        comp_oper=alarms_params[alarm][alarm_metric+"ComparisonOperator"]["Default"]
                        evaluation_period=int(alarms_params[alarm][alarm_metric+"EvaluationPeriods"]["Default"])
                        statistics=alarms_params[alarm][alarm_metric+"Statistic"]["Default"]
                        threshold=float(alarms_params[alarm][alarm_metric+"Threshold"]["Default"])
                        
                        create_alarms(secondary_cw_client,feature_name,alarm,secondary_sns_topic,statistics,secondary_db_identifier,periods,evaluation_period,threshold,comp_oper)
                        print("Created RDS alarm {}".format(alarm))
                    
                lambda_arn=context.invoked_function_arn.split(" ")[0]
                update_rule(secondary_event_bridge_client,rule_name, lambda_arn,'{"secondary":"wait_rds_active"}',"CheckRdsStatus")
                enable_event_bridge_rule(secondary_event_bridge_client,rule_name)
                print("Enabled {} eventbridge rule".format(rule_name))
                      
        if "secondary" in event:
            if event["secondary"].lower()=="wait_rds_active":
                ssm_param_value=json.loads(str(get_parameter(secondary_ssm_client,ssm_param)).replace("'",'"'))
                secondary_db_identifier=ssm_param_value["secondary_db_identifier"].lower()
                db_identifier=ssm_param_value["db_identifier"].lower()
                db_instances=get_db_instance(secondary_rds_client)
                for db in db_instances:
                
                    if db['DBInstanceIdentifier']==secondary_db_identifier.lower() and db['DBInstanceStatus'].lower()=="available":
                        print("DB instance {} is in available state".format(secondary_db_identifier))
                        
                        print("Creating event subscription for the DB Instance")
                        create_event_subscription(secondary_rds_client,feature_name+secondary_db_identifier,secondary_db_identifier,secondary_sns_topic,tags)
                        
                        print("DB Instance failover is successful")
                        endpoint_url=db['Endpoint']['Address']

                        title="RDS-Postgresql instance {} - Failover".format(db_identifier)
                        servicenow_msg={"endpoint_url":endpoint_url,"lambda":"DB instance {} failover to region {} with db identifier {}".format(db_identifier,secondary_region,secondary_db_identifier),"snow_title":title}
                        invoke_lambda(secondary_lambda_client,create_incident_lambda_arn,servicenow_msg)

                        disable_event_bridge_rule(secondary_event_bridge_client,rule_name)
                        print("Disabled event bridge rule: {}".format(rule_name))
                        
                    
                    elif db['DBInstanceIdentifier']==secondary_db_identifier.lower() and db['DBInstanceStatus'] in ["creating", "backing-up", "modifying", "starting","configuring-log-exports"]:
                        
                        print("DB instance {} is creating, Waiting for Creation.".format(secondary_db_identifier.lower()))
                
    
        if "detail" in event:
            if event["detail"]["eventTypeCategory"].lower()=="issue" and event["detail"]["statusCode"].lower()=="closed":
                db_instances=get_db_instance(secondary_rds_client)
                for db in db_instances:
                
                    if db['DBInstanceIdentifier']==secondary_db_identifier.lower() and db['DBInstanceStatus'].lower()!="available":
                        print("Primary region available, Failover cancelled.")
                        disable_event_bridge_rule(secondary_event_bridge_client,rule_name)
                        print("Disabled event bridge rule: {}".format(rule_name))
                        sleep(120)
                        delete_rds_instance(secondary_rds_client,secondary_db_identifier.lower())
                        print("Deleting rds instance in secondary region.")
                        db_alarms=[]
                        alarms_params=item["Alarms"]
                        db_alarms.extend(feature_name+"-"+alarm+"-"+secondary_db_identifier.lower() for alarm in alarms_params.keys())    
                        delete_alarms(secondary_cw_client,db_alarms)
                        print("Deleted all RDS instance alarms in secondary region")
                        exit()

                
                print("Deleting resources in primary region")
                db_identifier=item['RDSParameters']['DBInstanceIdentifier']['Default'].lower()
                delete_rds_instance(primary_rds_client,db_identifier.lower())
                
                db_alarms=[]
                
                nested_stack_id=get_stack_resource(primary_cf_client,feature_stack,primary_nested_stack_logical_id)
                
                db_alarms.extend(get_stack_resource(primary_cf_client,nested_stack_id,alarm.replace("Alarm","")) for alarm in alarms_params.keys())
    
                if not get_alarms(primary_cw_client, db_alarms):
                    db_alarms=[]
                    alarms_params=item["Alarms"]
                    db_alarms.extend(feature_name+"-"+alarm+"-"+db_identifier.lower() for alarm in alarms_params.keys())
                delete_alarms(primary_cw_client,db_alarms)

                primary_event_subscription=get_stack_resource(primary_cf_client,nested_stack_id,"DatabaseEventSubscription")
                if not get_subscriptions(primary_rds_client, primary_event_subscription):
                    primary_event_subscription=feature_name+db_identifier.lower()
                delete_event_subscription(primary_rds_client,primary_event_subscription)
                
                print("Deleted Resources in Primary region.")

                if enable_backup_replication(primary_rds_client,secondary_region,"arn:aws:rds:"+secondary_region+":"+context.invoked_function_arn.split(":")[4]+":db:"+secondary_db_identifier.lower()):
                    print("Automated backup replication successful for region: {}".format(primary_region))
                else:
                    print("Auomated backup failed to enabled")

                lambda_arn=context.invoked_function_arn.split(" ")[0]
                sleep(320)
                update_rule(secondary_event_bridge_client,rule_name, lambda_arn,'{"primary":"wait_automated_backup"}',"CheckRdsStatus")
                enable_event_bridge_rule(secondary_event_bridge_client,rule_name)
                print("Enabled {} eventbridge rule".format(rule_name))
            
        if "primary" in event:
            if "wait_automated_backup" in event["primary"]:
                sleep(360)
                automated_backup_arn=get_automated_backup(primary_rds_client,secondary_db_identifier.lower())
                if not automated_backup_arn:
                    print("Automated backup not available for the DB instance: {}".format(secondary_db_identifier.lower()))
                    exit()
                    
                nested_stack_id=get_stack_resource(primary_cf_client,feature_stack,primary_nested_stack_logical_id)
                
                subnet_group=get_stack_resource(primary_cf_client,nested_stack_id,primary_subnet_gp_logical_name)
                sg_id=get_stack_resource(primary_cf_client,nested_stack_id,primary_sg_logical_name)
                
                create_pitr_rds(primary_rds_client,db_identifier.lower(),db_instance_class,subnet_group,db_multi_az,db_name,db_option_gp_name,[sg_id],db_iam_authentication,db_cw_logs,db_parameter_group,automated_backup_arn,int(db_allocatedstorage),tags,storage_type)
                print("RDS instance creating successfully in primary region")
                sleep(240)
                delete_rds_instance(secondary_rds_client,secondary_db_identifier.lower())
                print("Deleting instance in secondary region")

                alarms_params=item["Alarms"]
                for alarm in alarms_params.keys():
                    alarm_metric=alarm.replace("Database","").replace("Alarm","")
                    if alarms_params[alarm]["Apply"+alarm_metric+"Alarm"]:
                        
                        periods=alarms_params[alarm][alarm_metric+"Period"]["Default"]
                        comp_oper=alarms_params[alarm][alarm_metric+"ComparisonOperator"]["Default"]
                        evaluation_period=alarms_params[alarm][alarm_metric+"EvaluationPeriods"]["Default"]
                        statistics=alarms_params[alarm][alarm_metric+"Statistic"]["Default"]
                        threshold=alarms_params[alarm][alarm_metric+"Threshold"]["Default"]
                        
                        create_alarms(primary_cw_client,feature_name,alarm,"arn:aws:sns:"+primary_region+":"+context.invoked_function_arn.split(":")[4]+":"+primary_sns_topic,statistics,db_identifier,periods,evaluation_period,threshold,comp_oper)
                        print("Created RDS alarm {}".format(alarm))
                    
                lambda_arn=context.invoked_function_arn.split(" ")[0]
                update_rule(secondary_event_bridge_client,rule_name, lambda_arn,'{"primary":"wait_rds_active"}',"CheckRdsStatus")
                enable_event_bridge_rule(secondary_event_bridge_client,rule_name)
                print("Updated the event bridge rule: {}".format(rule_name))
                
            
        
        if "primary" in event:
            if event["primary"].lower()=="wait_rds_active":
                
                db_instances=get_db_instance(primary_rds_client)
                 
                for db in db_instances:
                    if db['DBInstanceIdentifier']==db_identifier.lower() and db['DBInstanceStatus'].lower()=="available":
                        print("DB instance {} is in available state".format(db_identifier.lower()))
                        
                        print("Creating event subscription for the DB Instance")
                        
                        create_event_subscription(primary_rds_client,feature_name+db_identifier.lower(),db_identifier.lower(),"arn:aws:sns:"+primary_region+":"+context.invoked_function_arn.split(":")[4]+":"+primary_sns_topic,tags)
                        
                        if enable_backup_replication(secondary_rds_client,primary_region,"arn:aws:rds:"+primary_region+":"+context.invoked_function_arn.split(":")[4]+":db:"+db_identifier.lower()):
                            print("Automated backup replication successful for region: {}".format(secondary_region))
                        else:
                            print("Auomated backup failed to enabled")
                        
                        print("Deleting resources in secondary region")
                        
                        #delete_rds_instance(secondary_rds_client,secondary_db_identifier.lower())
                        
                        db_alarms=[]
                        alarms_params=item["Alarms"]
                        db_alarms.extend(feature_name+"-"+alarm+"-"+secondary_db_identifier.lower() for alarm in alarms_params.keys())
                            
                        delete_alarms(secondary_cw_client,db_alarms)
                        print("Deleted all RDS instance alarms in secondary region")
                        
                        event_subscription=feature_name+secondary_db_identifier.lower()
                        
                        delete_event_subscription(secondary_rds_client,event_subscription)
                        print("Deleted Event subscription of the secondary rds instance")

                        print("DB Instance failback is successful")

                        endpoint_url=db['Endpoint']['Address']

                        title="RDS-Postgresql instance {} - Failback".format(secondary_db_identifier)
                        servicenow_msg={"endpoint_url":endpoint_url,"lambda":"DB instance {} failback to region {} with db identifier {}".format(secondary_db_identifier,primary_region,db_identifier),"snow_title":title}
                        invoke_lambda(secondary_lambda_client,create_incident_lambda_arn,servicenow_msg)
                        
                        disable_event_bridge_rule(secondary_event_bridge_client,rule_name)
                        print("Disabled event bridge rule: {}".format(rule_name))
                    
                    elif db['DBInstanceIdentifier']==db_identifier.lower() and db['DBInstanceStatus'] in ["creating", "backing-up", "modifying", "starting","configuring-log-exports"]:
                        print("DB instance {} is creating, Waiting for Creation.".format(db_identifier.lower()))
        """
        if "update_rds" in event:
            try:

                db_instances=get_db_instance(secondary_rds_client)
                ssm_param_value=json.loads(str(get_parameter(secondary_ssm_client,ssm_param)).replace("'",'"'))

                db_option_gp_name=ssm_param_value["db_option_gp_name"]
                db_instance_class=ssm_param_value["db_instance_class"]
                db_cw_logs=ssm_param_value["db_cw_logs"]
                db_parameter_group=ssm_param_value["db_parameter_group"]
                db_allocatedstorage=ssm_param_value["db_allocatedstorage"]
                db_iam_authentication=ssm_param_value["db_iam_authentication"]
                db_multi_az=ssm_param_value["db_multi_az"]
                secondary_db_identifier=ssm_param_value["secondary_db_identifier"]
                if not any(db['DBInstanceIdentifier']==secondary_db_identifier.lower() for db in db_instances):
                    print("DB instance Not present with name: {}".format(db_identifier))
                    print("Skipping the db instance update")
                else:
                    update_rds_instance(secondary_rds_client,secondary_db_identifier,db_option_gp_name,db_parameter_group,db_instance_class,db_cw_logs,db_allocatedstorage,db_iam_authentication,db_name,primary_sns_topic)
        """

            
    except Exception as e:
        print("Error-lambda_handler()",e)
            