"""
Lambda function that evaluates if any of the IAM Roles have full access policy attached
Sample Call:

{
   "version":"1.0",
   "invokingEvent":"{\"configurationItemDiff\":null,\"configurationItem\":{\"relatedEvents\":[],\"relationships\":[],\"configuration\":{\"path\":\"/\",\"roleName\":\"FeatureDeregisterAmisDele-rDxcmsDeregisterAmisLamb-15YYU7ISB15H3\",\"roleId\":\"AROATJHRNB7MEEQEQPCUC\",\"arn\":\"arn:aws:iam::225992052696:role/FeatureDeregisterAmisDele-rDxcmsDeregisterAmisLamb-15YYU7ISB15H3\",\"createDate\":\"2022-09-08T10:12:18.000Z\",\"assumeRolePolicyDocument\":\"%7B%22Version%22%3A%222012-10-17%22%2C%22Statement%22%3A%5B%7B%22Effect%22%3A%22Allow%22%2C%22Principal%22%3A%7B%22Service%22%3A%22lambda.amazonaws.com%22%7D%2C%22Action%22%3A%22sts%3AAssumeRole%22%7D%5D%7D\",\"instanceProfileList\":[],\"rolePolicyList\":[{\"policyName\":\"DxcmsDeregisterHardenedAmisPerms-ap-south-1\",\"policyDocument\":\"%7B%22Version%22%3A%222012-10-17%22%2C%22Statement%22%3A%5B%7B%22Action%22%3A%5B%22logs%3ACreateLogGroup%22%2C%22logs%3ADescribeLogGroups%22%2C%22logs%3ACreateLogStream%22%2C%22logs%3APutLogEvents%22%5D%2C%22Resource%22%3A%5B%22arn%3Aaws%3Alogs%3Aap-south-1%3A225992052696%3Alog-group%3A%2Faws%2Flambda%2Fdxcms-deregister-amis-delete-ami-snapshots%3A%2A%22%5D%2C%22Effect%22%3A%22Allow%22%7D%2C%7B%22Action%22%3A%5B%22ec2%3ACreateTags%22%2C%22ec2%3ACreateTags%22%2C%22ec2%3ADescribeImages%22%2C%22ec2%3ADescribeSnapshots%22%2C%22ec2%3ADeregisterImage%22%2C%22ec2%3ADeleteSnapshot%22%5D%2C%22Resource%22%3A%22%2A%22%2C%22Effect%22%3A%22Allow%22%7D%2C%7B%22Action%22%3A%5B%22ssm%3AGetParameter%22%5D%2C%22Resource%22%3A%5B%22arn%3Aaws%3Assm%3Aap-south-1%3A225992052696%3Aparameter%2FDXC%2FDeregisterAmisDeleteAmiSnapshot%2FAmiSnapshotDesc%22%5D%2C%22Effect%22%3A%22Allow%22%7D%5D%7D\"}],\"attachedManagedPolicies\":[],\"permissionsBoundary\":null,\"tags\":[{\"key\":\"Owner\",\"value\":\"DXC\"},{\"key\":\"Application\",\"value\":\"FeatureDeregisterAmisDeleteAmiSnapshotsStack-AmisDeleteAmiSnapshots-1ACBMM3WLPG02\"},{\"key\":\"Name\",\"value\":\"rDxcmsDeregisterAmisLambdaRole\"}],\"roleLastUsed\":null},\"supplementaryConfiguration\":{},\"tags\":{\"Owner\":\"DXC\",\"Application\":\"FeatureDeregisterAmisDeleteAmiSnapshotsStack-AmisDeleteAmiSnapshots-1ACBMM3WLPG02\",\"Name\":\"rDxcmsDeregisterAmisLambdaRole\"},\"configurationItemVersion\":\"1.3\",\"configurationItemCaptureTime\":\"2022-09-08T10:13:35.549Z\",\"configurationStateId\":1662632015549,\"awsAccountId\":\"225992052696\",\"configurationItemStatus\":\"ResourceDiscovered\",\"resourceType\":\"AWS::IAM::Role\",\"resourceId\":\"AROATJHRNB7MEEQEQPCUC\",\"resourceName\":\"FeatureDeregisterAmisDele-rDxcmsDeregisterAmisLamb-15YYU7ISB15H3\",\"ARN\":\"arn:aws:iam::225992052696:role/FeatureDeregisterAmisDele-rDxcmsDeregisterAmisLamb-15YYU7ISB15H3\",\"awsRegion\":\"global\",\"availabilityZone\":\"Not Applicable\",\"configurationStateMd5Hash\":\"\",\"resourceCreationTime\":\"2022-09-08T10:12:18.000Z\"},\"notificationCreationTime\":\"2022-09-27T09:08:26.406Z\",\"messageType\":\"ConfigurationItemChangeNotification\",\"recordVersion\":\"1.3\"}",
   "resultToken":"eyJlbmNyeXB0ZWREYXRhIjpbODcsNDEsLTcsMTE3LC0yNCwtODIsLTEyLDYxLC0xMTgsLTIzLDY2LC0zMCwtNzUsLTYzLDgwLDExMSwzNiwtNzcsLTQ1LC0xMjUsMTAsLTQ3LDEwOSwtNTgsNzUsMTAsNTYsMjYsLTMwLDczLC0xMTEsMTYsOTMsLTgsMTA3LC04LC01NiwtMTIwLC03MCwxMTYsNTgsMjAsLTM1LC04NSwtNTIsLTQ4LC0zLC0xMDAsNjEsMzMsMTI0LDExOSwyNiwzMCwtNTgsOTIsNzgsMCwtNDgsLTExNiwtNCwtMTA5LDAsLTQ5LDEzLC0xMCwtNjgsMTEsMzQsNjUsODAsLTI1LDM2LDYsNzEsLTEwMywyLDEwNiwtMTI1LC02MiwtMiwxMTAsMTQsLTEyNSwxMjcsLTEyNSwtMzMsNTksMTksLTExMSw2MCwxNCwtMTIwLDE2LDQwLDI0LC0xMTgsLTEyNCwtODAsMTE5LC00OCw0NSw3MCw1OSw2NiwxMDIsLTM2LC0yNiwxMiwxMDIsMTAxLC00MywtMTYsMTIxLDQ1LDExMSw0OCwtNTMsLTM5LDU3LDc3LC00NywxMDYsODYsNjgsLTExMywtMjcsMTI0LC01OCwtMTgsNjgsMTAyLC0xNSwtMTExLC0xMDgsMiw4MywtNTYsLTk0LC03MCwtMTA4LC01NiwtOCwyOCw0MSwxMDYsNTksNCwtMTAzLC02OCwtNzgsLTI3LDYzLDUsLTk3LDEwMiwtOTYsLTI0LC05OCwtMTIyLC0yMywxLDM1LDEwMSwyOSwwLC0xOSwtNzEsNTYsNzgsLTU5LDY2LC0xMDMsMTE5LC05OCwtODMsOTQsMSw5OCwtMzMsMTE2LDEwOCwyNSw0MSwtMTA5LDQ5LC03MCw1NywyMCwwLDMxLDExMCw1MiwyOCwxMiw0NCw5NSw3Nyw5NSwtOTEsLTEyMiw0MSw4Miw2NSwxMDUsLTg1LC04MCwzMiw0NiwtNzksMTAwLC03NywxMjEsMTA5LDE1LDYzLDcwLDY4LDk1LC03MywtMTEzLC0xLDI4LC05OSwzNSw3LC04NiwtMTE0LDM0LDg5LC01NSwyOSwtOTIsNjcsLTI3LDEsLTMzLC0xMjQsLTMsMTE4LC0yNSwxMDIsLTIxLC05Myw3MywtOTEsMTA1LDUyLC0zMiwyMSw3OCwtMTIwLC05MiwxMTMsLTMwLDk1LC04NSwxOSwtOSw4NiwtNjMsMzYsNDYsMTI0LDU3LDQyLC0zNSwxMTksLTEwNiwtMTAxLC01NSwtNzksLTI2LC05NSwzMywtOCwtMTIsNTYsMjgsNjIsLTE0LDEwNiwtNDEsLTEyNyw1OSwtMzEsODcsLTM5LDE4LC0xMCwtMTAzLDM2LDM3LDI5LDU3LC00NCw2MywtMTAzLDUzLC04OSwtMTE3LDExOCwtMTEyLDY1LDg5LC05OCwzOSwyNywxMDMsLTEwOCwtNDEsMTcsODQsLTY3LDM3LDU3LDQzLC04Niw5NCw0OCwtNDMsMjMsLTE4LDc5LC04MCwzLDEyMCwtODQsLTIwLDc1LDExNyw4LC0zMCwtNTYsMTI0LC0yMCwxMjIsLTExMSw0MiwtOTgsMTksLTEyMCwtMjEsLTk0LDM4LC00NCwyOCwtMzgsLTU3LDk5LDExNSw1MCwtOTUsODEsOTgsNywxMywyMyw2MywxMjYsLTEyMCw3MiwtOTQsLTU0LDcsMTQsMTIzLC01MywtODUsNTEsLTgxLC05LC0zMSw3MCwtNzEsMTA2LC0zNywxNiwyNCw4OCwtMjMsNCwtMTA5LDU3LDQxLC00OCwzNywtNTcsNzYsLTI1LDMyLC01MSwtMTE5LC02Miw5MCw1Myw2MiwtMTI4LC00Myw1LC05OSwtNjksLTk0LC01NywtMzAsLTk2LC01OCwtMTA1LC0xMDIsLTEwNCwtMTcsNTIsLTQsLTk5LC02MywtNDQsOTksNDEsNDMsMTAxLDksMzUsNDQsLTEwMiwzMiwtMjAsLTU3LDEwNCwtMTgsNTYsLTMyLDUxLDU4LC00OSwxNCwxNCwtMTYsLTE4LDM0LC0xMjAsLTc3LDEwOSwtMTA2LC05MCwtNDYsNDUsMTA0LC0zMCwtMTI3LDgwLC00NiwtMTAyLDU5LC0xMDcsLTUxLC03MCw4OSwxMjUsLTU5LDE4LDg2LDM0LC0xMTMsLTY1LC0xLDE3LC0xOSwtNDUsLTc5LC0yNCwtMjksLTMsLTUyLDQ5LC05NCwtODIsNTQsLTU0LDEwOSwtNTgsMTA5LDExMywxMTcsLTQwLDEsMTA0LC00OCw3NSwtNzUsLTIxLC0xOCw3MCw4NCwtNjgsMTMsNzIsLTcsODEsLTY2LC04MSwtNTYsLTM5LC0yMiwxMjEsLTYxLC01MiwtODgsLTUsMzUsLTg1LDkxLC0zMiw4MSw0OCwtMTE4LC05NSw1MSwtMTIsMTUsMTAxLC0yMiw2MiwxMTIsNzEsNzksMTcsLTg4LDUxLDM0LC02NCwtNDMsNDksLTQwLC05NCwtNzcsLTY3LDI0LC0xMDksMTIyLDEwOCwtNTgsMTIwLC0xNSwxMTAsLTg2LDY1LDksLTUyLDEyMiw4NSwxMTAsNjEsLTgyLC0xMjUsLTQ4LDI2LC0yLDY3LDEwNiw1OSw1MCw4NiwtNTQsLTExLDExOSw1NSwtMjcsLTIwLDExOSwxMCwxNiw0LDMzLC00NSw1MiwxMjcsNjcsLTczLDU5LDExNywtOTYsLTEyMywtNDcsLTEwNywtNjcsLTYwLDM4LDQyLDExNSwtMzQsNzMsNTIsLTc1LC0xMjUsOSwzOSwtNTYsMTExLDE2LDIzLC0xNSwtMTA2LDEyMCwxMywyOSw0MiwxMjAsLTQzLC0xMDQsNDgsLTExMiwtMTYsODMsLTE0LC05NCw2MCwxNywtMTExLDU0LC00NCwtNjksLTEwMyw3MywtMTA0LC0xMTMsLTE5LC0xMF0sIm1hdGVyaWFsU2V0U2VyaWFsTnVtYmVyIjoxLCJpdlBhcmFtZXRlclNwZWMiOnsiaXYiOlstNTgsNTQsLTQsMTAwLDAsMTAwLDEyMCwtNjAsMjgsLTEwOCwtOTUsODcsLTE5LC0yMiwxMjAsLTMzXX19",
   "eventLeftScope":false,
   "executionRoleArn":"arn:aws:iam::225992052696:role/FeatureConfigServiceStack-AWSConfig-rAWSConfigRole-L4PLQM9PYPWU",
   "configRuleArn":"arn:aws:config:eu-west-2:225992052696:config-rule/config-rule-ut1jhh",
   "configRuleName":"FeatureConfigRuleFullAccessP-rFullAccessConfigRule-1RWRP54DGH0NI",
   "configRuleId":"config-rule-ut1jhh",
   "accountId":"225992052696"
}

"""
from config_full_access_policy import (FullAccessPolicyEvaluation)


def lambda_handler(event, context):
    print('received event:',event)
    
    evaluation = FullAccessPolicyEvaluation()
    return evaluation.handler_impl(event, context)
