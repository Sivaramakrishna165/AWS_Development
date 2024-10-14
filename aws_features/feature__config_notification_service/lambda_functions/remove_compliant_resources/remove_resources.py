#
# Compares the Non-Compliant resources returned from AWS Config
# to the entries in DynamoDB.  If there is a resource that
# is in compliance (i.e. not in the list of non-compliant resources),
# delete the resource entry in DynamoDB.
#
# Trigger Type: Step Function State [RemoveCompliantResources]
# Scope: Non-Compliant Resources in AWS Config
# Accepted Parameter: None
#

from __future__ import print_function
import boto3


class GetParameterException(Exception):
    pass


class GetTableException(Exception):
    pass


class ScanTableException(Exception):
    pass


class ConfigStatusExecutionException(Exception):
    pass


class DeleteItemException(Exception):
    pass


class RemoveCompliantResources:
    def __init__(self):
        session = boto3.Session()
        self.config = session.client('config')
        self.dynamodb = session.resource('dynamodb')
        self.ssm = session.client('ssm')
        self.offerings_config_rules_prefix = 'FeatureConfigRule'

    def grab_db_elements(self, table):
        resources = ''
        try:
            response = table.scan(
                           IndexName='Notifications',
                           AttributesToGet=['ResourceId', 'ConfigRuleName']
                       )
            resources = response['Items']
            while True:
                if response.get('LastEvaluatedKey'):
                    response = table.scan(
                                   IndexName='Notifications',
                                   AttributesToGet=[
                                       'ResourceId',
                                       'ConfigRuleName'
                                   ],
                                   ExclusiveStartKey=(
                                       response['LastEvaluatedKey']
                                   )
                               )
                    resources += response['Items']
                else:
                    break
        except boto3.exceptions.botocore.client.ClientError as e:
            print("Error scanning table: %s" % e)
            raise ScanTableException("Error scanning table: %s" % e)

        return resources

    def db_config_diff(self, db_resources):
        config_resources = []
        removal = []
        extra_args = {}
        while True:
            try:
                results = self.config.describe_config_rule_evaluation_status(**extra_args)
            except boto3.exceptions.botocore.client.ClientError as e:
                print("Error getting Config evaluations: %s" % e)
                raise ConfigStatusExecutionException("Error: %s" % e)

            for config_rule in results['ConfigRulesEvaluationStatus']:
                if(self.offerings_config_rules_prefix not in config_rule['ConfigRuleName']):
                    continue
                print('Config Rule - ',config_rule['ConfigRuleName'])
                non_compliant = self.config.get_compliance_details_by_config_rule(
                                    ConfigRuleName=config_rule['ConfigRuleName'],
                                    ComplianceTypes=['NON_COMPLIANT'])
                for result in non_compliant['EvaluationResults']:
                    res_id = (result['EvaluationResultIdentifier']
                            ['EvaluationResultQualifier']
                            ['ResourceId'])
                    config_name = (result['EvaluationResultIdentifier']
                                ['EvaluationResultQualifier']
                                ['ConfigRuleName'])
                    config_resources.append(
                        {str('ResourceId'): res_id,
                        str('ConfigRuleName'): config_name})

            for d_res in db_resources:
                match = None
                for c_res in config_resources:
                    if d_res == c_res:
                        match = True
                if not match:
                    removal.append(d_res)
                    print("Resource to be removed: %s" % str(d_res))

            if 'NextToken' in results:
                extra_args['NextToken'] = results['NextToken']
            else:
                break

        return removal

    def handler_impl(self, event, context):
        print('Function Name: ' + context.function_name)
        print('Function Version: ' + context.function_version)
        try:
            table_param = self.ssm.get_parameter(
                              Name='/DXC/ConfigService/DynamoDBTableName'
                          )
        except boto3.exceptions.botocore.client.ClientError as e:
            print("Error getting SSM parameter: %s" % e)
            raise GetParameterException("Error: %s" % e)
        try:
            table = self.dynamodb.Table(table_param['Parameter']['Value'])
        except boto3.exceptions.botocore.client.ClientError as e:
            print("Error accessing DynamoDB table: %s" % e)
            raise GetTableException("Error: %s" % e)
        stored_resources = self.grab_db_elements(table)
        if len(stored_resources) > 0:
            resources = self.db_config_diff(stored_resources)
            if len(resources) > 0:
                for element in resources:
                    try:
                        table.delete_item(
                            Key={
                                'ConfigRuleName': element['ConfigRuleName'],
                                'ResourceId': element['ResourceId']
                            }
                        )
                        print("Deleted ResourceId: %s" % element['ResourceId'])
                    except boto3.exceptions.botocore.client.ClientError as e:
                        print("Error deleting item: %s" % e)
                        raise DeleteItemException("Error: %s" % e)
            else:
                print("DynamoDB table has all non-compliant resources.")
        else:
            print("No resources present in DynamoDB table: " +
                  str(table_param['Parameter']['Value']))
