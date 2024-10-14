'''
Boto Helper class contain all the supported aws api operations
'''

import boto3
import time

class primary_boto_helper():
    
    #To get primary vpc id
    def get_primary_vpc_id(self,ec2_client):
        
        try:
            response = ec2_client.describe_vpcs()
            vpc_list = response['Vpcs']
            
            for vpc in vpc_list:
                for tag in vpc['Tags']:
                    if tag['Key'] == 'Name' and tag['Value'] == 'Workload VPC v2':
                        vpc_id = vpc['VpcId']            
            
            return vpc_id
        
        except Exception as e:
            print('ERROR -', str(e))
            raise e
    
    #To get the primary subnet id
    def get_primary_subnet_id(self,ec2_client, vpcid):
        
        try:
            response = ec2_client.describe_subnets()
            subnet_lst = response['Subnets']
            
            subnet_id = []
            for subnet in subnet_lst:
                if subnet['VpcId'] in vpcid:
                    for tags in subnet['Tags']:
                        if tags['Key'] == 'SubnetType' and tags['Value'] == 'Private':
                            subnet_id.append(subnet['SubnetId'])
                            
            return subnet_id
        
        except Exception as e:
            print('ERROR -', str(e))
            raise e
    
    #To accept the peering connection
    def accept_peering_connection(self, ec2_client, peering_connection_id):
        
        try:
            response = ec2_client.accept_vpc_peering_connection(
            VpcPeeringConnectionId=peering_connection_id
            )
            
            print('The peering connection has been accepted')
            time.sleep(10)
            peering_connection_status = response['VpcPeeringConnection']['Status']['Code']
            print('The peering connection status is', peering_connection_status)
        
        except Exception as e:
            print('ERROR -', str(e))
            raise e
            
    #To get primary vpc info
    def get_vpc_info(self, ec2_client, vpc_id):
        
        try:
            response = ec2_client.describe_vpcs(
                VpcIds=[vpc_id]
                )
            return response
        
        except Exception as e:
            print('ERROR -', str(e))
            raise e
            
    #To fetch the route tables attached to the replication vpc
    def get_route_tables(self, ec2_client, vpcid):
        
        try:
            response = ec2_client.describe_route_tables()
            rtb_list = response['RouteTables']
            return rtb_list
            
        except Exception as e:
            print('ERROR -', str(e))
            raise e
            
    #To add the route to the route table
    def modify_route_table(self, ec2_client, cidr, routetable, peering_connection_id):
        
        try:
            response = ec2_client.create_route(
                DestinationCidrBlock=cidr,
                RouteTableId=routetable,
                VpcPeeringConnectionId=peering_connection_id
                )
        
        except Exception as e:
            print(str(e))
            
        finally:
            response = ec2_client.replace_route(
                DestinationCidrBlock=cidr,
                RouteTableId=routetable,
                VpcPeeringConnectionId=peering_connection_id
                )