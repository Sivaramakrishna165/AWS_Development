'use strict';

const aws = require('aws-sdk');
let config = new aws.ConfigService();
let ec2 = new aws.EC2();
const async = require('async');

//for testing only
function setRegion(regionName) {
    ec2 = new aws.EC2({region: regionName});
    config = new aws.ConfigService({region: regionName});
}

const PUBLIC_CIDR = '0.0.0.0/0';

// Helper function used to validate input
function checkDefined(reference, referenceName) {
    if (!reference) {
        throw new Error(`Error: ${referenceName} is not defined`);
    }
    return reference;
}

// Check whether the message type is OversizedConfigurationItemChangeNotification,
function isOverSizedChangeNotification(messageType) {
    
    console.log('for message type ' + messageType + ' checking oversided');
    checkDefined(messageType, 'messageType');
    return messageType === 'OversizedConfigurationItemChangeNotification';
}



function getConfiguration(resourceType, resourceId, configurationCaptureTime, callback) {
    config.getResourceConfigHistory({ resourceType, resourceId, laterTime: new Date(configurationCaptureTime), limit: 1 }, (err, data) => {
        if (err) {
            callback(err, null);
            return;
        }
        console.log('## looking at config item ' + JSON.stringify(data));
        const configurationItem = data.configurationItems[0];
        callback(null, configurationItem);
    });
}

// Convert the oversized configuration item from the API model to the original invocation model.
function convertApiConfiguration(apiConfiguration) {
    apiConfiguration.awsAccountId = apiConfiguration.accountId;
    apiConfiguration.ARN = apiConfiguration.arn;
    apiConfiguration.configurationStateMd5Hash = apiConfiguration.configurationItemMD5Hash;
    apiConfiguration.configurationItemVersion = apiConfiguration.version;
    apiConfiguration.configuration = JSON.parse(apiConfiguration.configuration);
    if ({}.hasOwnProperty.call(apiConfiguration, 'relationships')) {
        for (let i = 0; i < apiConfiguration.relationships.length; i++) {
            apiConfiguration.relationships[i].name = apiConfiguration.relationships[i].relationshipName;
        }
    }
    return apiConfiguration;
}

// Based on the message type, get the configuration item either from the configurationItem object in the invoking event or with the getResourceConfigHistory API in the getConfiguration function.
function getConfigurationItem(invokingEvent, callback) {
    
    checkDefined(invokingEvent, 'invokingEvent');
    if (isOverSizedChangeNotification(invokingEvent.messageType)) {
       const configurationItemSummary = checkDefined(invokingEvent.configurationItemSummary, 'configurationItemSummary');
        getConfiguration(configurationItemSummary.resourceType, configurationItemSummary.resourceId, configurationItemSummary.configurationItemCaptureTime, (err, apiConfigurationItem) => {
            if (err) {
                callback(err);
            }
            const configurationItem = convertApiConfiguration(apiConfigurationItem);
            callback(null, configurationItem);
       });
    } else {
        checkDefined(invokingEvent.configurationItem, 'configurationItem');
        callback(null, invokingEvent.configurationItem);
    }
}

// Check whether the resource has been deleted. If the resource was deleted, then the evaluation returns not applicable.
function isApplicable(configurationItem, event) {
    checkDefined(configurationItem, 'configurationItem');
    checkDefined(event, 'event');
    const status = configurationItem.configurationItemStatus;
    const eventLeftScope = event.eventLeftScope;
    return (status === 'OK' || status === 'ResourceDiscovered') && eventLeftScope === false;
}


//This rule returns putEvaluationsRequest with compliance or non-compliance for various 
//evaluated items
function evaluateChangeNotification(configurationItem, ruleParameters, event, callback) {

    checkDefined(configurationItem, 'configurationItem');
    //  checkDefined(configurationItem.configuration, 'configurationItem.configuration');
    //  checkDefined(ruleParameters, 'ruleParameters');

    if (isApplicable(configurationItem, event)) {

       if (configurationItem.resourceType == 'AWS::VPC::SecurityGroup') {
           processSecurityGroupChange(configurationItem, event, callback);
           return;
       }
       else if (configurationItem.resourceType == 'AWS::EC2::Instance') {
           processInstanceChange(configurationItem, event, callback);
           return;
       }
       else {
          //this should not be called with any other asset type so return NOT_APPLICABLE
          callback(null, defaultConfigurationItemNotApplicable(configurationItem, event));
       }
     }
     else {
          callback(null, defaultConfigurationItemNotApplicable(configurationItem, event));
     }
}


function getQuickSilverInstancesWithSecurityGroups(callback) {

    let nextToken = null;
    let params = {};
    let instancesIdsWithSecurityGroups = [];
    async.doWhilst(
        function (wcallback) {
            async.retry({
                errorFilter: function (err) {
                    var retryable = err.retryable;
                    return (retryable && retryable == true);
                },
                times: 8,
                interval: function (retryCount) {
                    return 1000 * retryCount; //  1 seconds, 2 seconds, 4 seconds, etc.
                }
            },
                function (dicb) {
                   ec2.describeInstances(params, function(err, data) {
                         if (err) {
                           console.log(err, err.stack);
                           dicb(err);
                         }
                         else  {

                            nextToken = data.NextToken;
                            for (let res = 0; res < data.Reservations.length; res++) {
                                let instances = data.Reservations[res].Instances;
                                for (var inst = 0; inst < instances.length; inst++) {
                                    //determine security groups then add instance and securityGroups to array 
                                    instances.forEach(function(x) {
                                        instancesIdsWithSecurityGroups.push({ 'instanceId' : x.InstanceId, 'securityGroups' : x.SecurityGroups });
                                    });
                                 }
                             }
                             dicb(null);
                         }
                       });
                },
                function (err, result) { //  Error on describeInstances:
                    if (err) {
                        wcallback(err);
                    } else {
                        wcallback(null);
                    }
                });
        },
        function () {
            params.NextToken = nextToken;
            return (nextToken != null);
        },
        function (werr, results) {
            //log issue (if present) but return as many instances as possible for the check
            callback(null, instancesIdsWithSecurityGroups);
        });
}

function getSecurityGroupsForInstance(instanceId, callback) {

    var params = { InstanceIds : [instanceId] };
    ec2.describeInstances(params, function(err, data) {
      if (err) {
        console.log(err, err.stack);
        callback(err);
      }
      else  {

         let securityGroupIds = [];

         try {

           data.Reservations[0].Instances[0].NetworkInterfaces.forEach(function(networkInterface) {
              networkInterface.Groups.forEach(function(securityGroup) {
                securityGroupIds.push(securityGroup.GroupId);
              });
           });
         }
         catch(e) {
            console.log('error issue finding security groups for instance ' + instanceId);
         }
         callback(null,securityGroupIds);
      }
    });
}


//if the security group has a public cidr look for instances that have this 
//security group attached to them.. these will be non-compliant instances,
//return the instance id and its security groups
function determineInstancesWhichHaveIndicatedSecurityGroup(instancesWithSecurityGroups, securityGroupId, callback) {

   let instanceIds = [];
   instancesWithSecurityGroups.forEach(function(instance) {
     if (instance.SecurityGroups) {
       looper: for (let a = 0; a < instance.SecurityGroups.length; a++) {
          if (instance.SecurityGroups[a].Groupid == securityGroupId) {
            instanceIds.push(instance);
            break looper;
          }
       }
     }
   });  
   callback(null, instanceIds);
}

function processSecurityGroupChange(configurationItem, event, callback) {

    //get security group id
    let securityGroupId = configurationItem.resourceId;

             async.waterfall([
                function(wcb) {
                   getQuickSilverInstancesWithSecurityGroups(wcb);
                },
                function(instancesWithSecurityGroups, wcb) {
                   determineInstancesWhichHaveIndicatedSecurityGroup(instancesWithSecurityGroups, securityGroupId, wcb);
                },
                function(instancesWithSecurityGroups, wcb) {

		   //create a map of security groups to a boolean indicating if they have the public cidr
                   //this will be a map with one entry per security group that is associated with any instance
                   //that was associated with the changed security group that resulted in this lambda being called.
                   let securityGroupMap = new Map();
                   instancesWithSecurityGroups.forEach(function(p) {
                        p.SecurityGroups.forEach(function(k) {
                          securityGroupMap.set(k.GroupId, false);
                        });
                   }); 
                  
                  async.each(securityGroupMap.keys(), function(key, cb) {
                     securityGroupContainsCidr(securityGroupId, PUBLIC_CIDR, function(err, result) {
                         //TODO think about errors 
                         securityGroupMap.set(key, result);    
                         cb(null);
                     }); 
                  },
                  function(err) {
                     console.log('security group map set ');
                     console.log(JSON.stringify(securityGroupMap));
                     wcb(null, instancesWithSecurityGroups, securityGroupMap);
                  });
                },
                function(instancesWithSecurityGroup, securityGroupMap, wcb) {

	           //set instance compliance based upon the presence of the public cidr in its security group
                   let compliantIds = [];
                   let nonCompliantIds = [];
                   async.each(instancesWithSecurityGroup, function(instance, cb) {
                      let nonCompliant = true;
                      for (let a = 0; a < instance.SecurityGroups.length; a++) {
                         if (securityGroupMap.get(instance.SecurityGroups[a].Groupid)) {
                            nonCompliant.push(instance.InstanceId);
                            cb(null);
                            return;
                         }
                      }
                      compliantIds.push(instance.InstanceId);
                      cb(null);
                      return; 
                  },
                  function(err) {
                      wcb(null, compliantIds, nonCompliantIds);
                  });
                }
             ],
             function(err, compliantIds, nonCompliantIds) {
                if (err) {
                   //this should rarely happen we want to log this but still return as much compliance info
                   //as possible
                }
              
                if (compliantIds.length == 0 && nonCompliantIds == 0) {
                   callback(null, defaultConfigurationItemNotApplicable(configurationItem, event));
                   return;
                }
                else {

                   let compliantPutEvaluations = null;
                   let nonCompliantPutEvaluations = null;
                   if (compliantIds && compliantIds.length > 0) {
                      compliantPutEvaluations =  buildPutEvaluationsRequest(compliantIds, 'AWS::EC2::Instance', 'COMPLIANT', configurationItem.configurationItemCaptureTime, event);
                   }
              
                   if (nonCompliantIds && nonCompliantIds.length > 0) {
                      nonCompliantPutEvaluations = buildPutEvaluationsRequest(compliantIds, 'AWS::EC2::Instance', 'NON_COMPLIANT', configurationItem.configurationItemCaptureTime, event);
                   }

                   if (compliantPutEvaluations) {
                     if (nonCompliantPutEvaluations) {
                       callback(null, compliantPutEvaluations.concat(nonCompliantPutEvaluations));
                       return;
                     }
                     else {
                       callback(null, compliantPutEvaluations);
                       return;
                     }
                   }
                   else if (nonCompliantIds) {
                      callback(null, nonCompliantPutEvaluations);
                      return;
                   }
                   else {
                      //this really should not happen
                     callback(null, defaultConfigurationItemNotApplicable(configurationItem, event));
                     return;
                   }
                 }
              });
}

//look at each security group associated with the instance any security
//group has the public cidr the instance is non-compliant
function processInstanceChange(configurationItem, event, callback) {

    async.waterfall([
        function(cb) {
            getSecurityGroupsForInstance(configurationItem.resourceId, cb);
        },
        function(securityGroupIds, cb) {
     async.some(securityGroupIds, function(securityGroupId, mcb) {
         securityGroupContainsCidr(securityGroupId, PUBLIC_CIDR, mcb); 
       },
       function(err,result) {
         if (err) {
            cb(err);
         }
         else {
             cb(null, result);
         }
       })
        }
       ],
       function(err, publicCidrFound) {
          
          if (err) {
              callback(err);
          }
          else {
              if (publicCidrFound) {
                //security group contains PUBLIC_CIDR so the instance is non-compliant 
                callback(null, configurationForBaseItem(configurationItem, 'NON_COMPLIANT', event)); 
               }
               else {
                callback(null, configurationForBaseItem(configurationItem, 'COMPLIANT', event)); 
               }
          }
       });
}

function configurationForBaseItem(configurationItem, compliance, event) {

   return buildPutEvaluationsRequest(
             [ configurationItem.resourceId ], 
             configurationItem.resourceType, 
             compliance, 
             configurationItem.configurationItemCaptureTime, 
             event);

}

//there is no async io in this call this is assumed
function defaultConfigurationItemNotApplicable(configurationItem, event) {

   return buildPutEvaluationsRequest(
             [ configurationItem.resourceId ], 
             configurationItem.resourceType, 
             'NOT_APPLICABLE', 
             configurationItem.configurationItemCaptureTime, 
             event);
}

//there is no async io in this call this is assumed
function buildPutEvaluationsRequest(itemResourceIds, resourceType, complianceType, itemCaptureTime, event) {

    let putEvaluationsRequest = {};
    putEvaluationsRequest.Evaluations = [];
    itemResourceIds.forEach(function(item) {
        putEvaluationsRequest.Evaluations.push( 
          {
                ComplianceResourceType: resourceType,
                ComplianceResourceId: item,
                ComplianceType: complianceType,
                OrderingTimestamp: itemCaptureTime,
          }
        );
    });

    putEvaluationsRequest.ResultToken = event.resultToken;
    return putEvaluationsRequest;
}
 
function securityGroupContainsCidr(securityGroupId, Cidr, callback) {

   var params = { GroupIds: [ securityGroupId ]};
   ec2.describeSecurityGroups(params, function(err, data) {

     if (err) {
         console.log(err, err.stack);
         callback(err);
         return;
     }
     else {

       //deliberately not using forEach
       if (data.SecurityGroups) { 
         for (var a = 0; a < data.SecurityGroups.length; a++) {
            if (data.SecurityGroups[a] && data.SecurityGroups[a].IpPermissions) {
              for (var b = 0; b < data.SecurityGroups[a].IpPermissions.length; b++) {
                if (data.SecurityGroups[a].IpPermissions[b] && data.SecurityGroups[a].IpPermissions[b].IpRanges) {
                   for (var c = 0; c < data.SecurityGroups[a].IpPermissions[b].IpRanges.length; c++) {
                      if (data.SecurityGroups[a].IpPermissions[b].IpRanges[c].CidrIp == Cidr) {
                        callback(null, true);
                        return;
                      }
                   }
                }
              }
            }
         }
       }
       callback(null, false); 
       return;
    }
  });
}

function safeJsonParse(jsonString) {
  try {
    const parsedData = JSON.parse(jsonString);
    return parsedData;
  } catch (error) {
    console.error('Error parsing JSON:', error);
    throw new Error('Invalid JSON input');
  }
}

// Receives the event and context from AWS Lambda.
exports.handler = (event, context, callback) => {
    //console.log('Event Received - ',event);
    console.log('Event:', JSON.stringify(event, null, 2));
    checkDefined(event, 'event');
    //let invokingEvent = JSON.parse(event.invokingEvent);
    let invokingEvent = safeJsonParse(event.invokingEvent);
    let ruleParameters = null;
    if (event.ruleParameters) {
       ruleParameters = JSON.parse(event.ruleParameters);
    }
    getConfigurationItem(invokingEvent, (err, configurationItem) => {
        if (err) {
            callback(err);
        }
        
        evaluateChangeNotification(configurationItem, ruleParameters, event, (err, putEvaluationsRequest) => {

            if (err) {
              callback(err);
            }
            
            console.log('RESULTS' + JSON.stringify(putEvaluationsRequest));
            
            // Sends the evaluation results to AWS Config.
            config.putEvaluations(putEvaluationsRequest, (error, data) => {
                if (error) {
                    callback(error, null);
                } else if (data.FailedEvaluations.length > 0) {
                    // Ends the function if evaluation results are not successfully reported to AWS Config.
                    callback(JSON.stringify(data), null);
                } else {
                    callback(null, data);
                }
            });
        });
    });
};

