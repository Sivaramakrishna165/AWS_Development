'use strict';

const aws = require('aws-sdk');
let cloudformation = new aws.CloudFormation();
let ec2 = new aws.EC2();

//This should be identifier unique to the custom resource vendor
let physicalResourceId = 'BastionTermExpired123456789abcdefg!#$';

//HELPER FUNCTIONS
function helperGetOutputKeyValue(stack, keyname) {
    for (let i in stack.Outputs) {
        if (stack.Outputs[i].OutputKey == keyname) { return stack.Outputs[i].OutputValue; }
    }   
    return null;
}

function helperStackHasOutputKeyWithValue(stack, keyname, value) {
    return helperGetOutputKeyValue(stack, keyname) == value;
}

//send response back to the cloud formation (stack)
//With custom actions under Cloud formation we normally want
//to send a responseStatus of 'SUCCESS' or the entire stack will get
//rolled back.
function sendResponse(event, context, responseStatus, responseStatusReason, responseData) {
 
 return new Promise(function(resolve, reject){
     
    try
    {
      let customResourceProviderResponse = JSON.stringify({
        'Status': responseStatus, //SUCCESS or FAILED
        'Reason': responseStatusReason,
        'PhysicalResourceId': physicalResourceId,
        'StackId': event.StackId,
        'RequestId': event.RequestId,
        'LogicalResourceId': event.LogicalResourceId,
        'Data': responseData
      });
 
      let https = require("https");
      let url = require("url");
 
      let parsedUrl = url.parse(event.ResponseURL);
      let options = {
        hostname: parsedUrl.hostname,
        port: 443,
        path: parsedUrl.path,
        method: "PUT",
        headers: {
            "content-type": "",
            "content-length": customResourceProviderResponse.length
        }
      };
 
      let request = https.request(options, function(response) {
        console.log("Status code: " + response.statusCode);
        console.log("Status message: " + response.statusMessage);
        resolve('send command to cloud formation successful:: ' + response.statusMessage);
      });
 
      request.on("error", function(error) {
        console.log("issue sending response to cloud formation:: " + error); 
        reject("issue sending response to cloud formation:: " + error);
      });
 
      request.write(customResourceProviderResponse);
      request.end();
    }
    catch(exc) {
        reject('send command exception:: ' + exc);
    }
 });
}

//this returns a promise
function deleteStack(stack) {
  return new Promise(function(resolve, reject){
    try  
    {
      console.info('deleting stack with id ' + stack.StackId + ' and stack name ' + stack.StackName + ' as it has expired');
      var params = { StackName : stack.StackId };
      cloudformation.deleteStack(params, function(err, data) {
        if (err) {
          console.error('issue deleteing stack :: ' + stack.StackName);
          reject(err);
        }
        else {
         console.info('stack :: ' + stack.StackName + ' deleted successfully');
         resolve(data);      
        } 
      });
    }
    catch(exc) {
      reject(exc);
    }
  });
}

function isWindowsTarget(stack) {

return new Promise(function(resolve, reject){

  let instanceId = '';
  try {

    const randomUsername = helperGetOutputKeyValue(stack, 'RandomUsername');
    instanceId = helperGetOutputKeyValue(stack, 'TargetInstanceId');
    const cidrIp = helperGetOutputKeyValue(stack, 'BastionPrivateCidrIp'); 
    const securityGroupId = helperGetOutputKeyValue(stack, 'TargetInstanceSecurityGroupId'); 
    const port = '3389';

    console.log('attempt to remove user account ' + randomUsername + ' from target instance ' + instanceId 
                + ' attempt to revoke ingress rule on security group ' + securityGroupId + ' for port ' + port 
                + ' with cidrip ' + cidrIp);

    const commandStr = "$User = \"" + randomUsername + "\";" 
        + "$Computername = $env:COMPUTERNAME;"
        + "$ADSIComp = [adsi]\"WinNT://$Computername\";"
        + "$ADSIComp.Delete(\"User\",$User)";

    let ssm = new aws.SSM();

    let responseMessage = '';
    let params = {
        DocumentName : 'AWS-RunPowerShellScript',
        InstanceIds : [ instanceId ],
        Comment : 'delete local user account on windows managed instance',
        Parameters : { 'commands' : [ commandStr ] }
      };

    ssm.sendCommand(params, function(err, data) {
       if (err) {
           responseMessage = 'attempt to remove user account ' + randomUsername + ' from target instance ' + instanceId 
                   + ' failed with error ' + err;
          console.error(responseMessage);
          reject(responseMessage);
       } 
       else {
          
          let revokeRequest = {
            CidrIp: cidrIp,
            FromPort: port,
            ToPort: port,
            IpProtocol: 'tcp',
            GroupId: securityGroupId
          };
         
          ec2.revokeSecurityGroupIngress(revokeRequest, function(err, data) {
            if (err) {
                responseMessage =  'attempt to revoke ingress rule on security group ' + securityGroupId + ' for port ' + port 
                + ' with cidrip ' + cidrIp + ' failed with error ' + err;
                console.error(responseMessage);
                reject(responseMessage);
            }
            else {
                responseMessage = 'Success attempt to remove user account ' + randomUsername 
                + ' from target instance ' + instanceId 
                + ' attempt to revoke ingress rule on security group ' + securityGroupId + ' for port ' + port 
                + ' with cidrip ' + cidrIp;
                resolve(responseMessage);
            } 
         });
       }
    });
  }
  catch(exp) {
    return reject('issue processing removal of ingress rule and local account for instance ' + instanceId + ' with error ' + exp);
  }
 });
}

function isLinuxTarget(stack) {

return new Promise(function(resolve, reject){

  let instanceId = '';
  try {

    const randomUsername = helperGetOutputKeyValue(stack, 'RandomUsername');
    instanceId = helperGetOutputKeyValue(stack, 'TargetInstanceId');
    const cidrIp = helperGetOutputKeyValue(stack, 'BastionPrivateCidrIp'); 
    const securityGroupId = helperGetOutputKeyValue(stack, 'TargetInstanceSecurityGroupId'); 
    const port = '22';

    console.log('attempt to remove user account ' + randomUsername + ' from target instance ' + instanceId 
                + ' attempt to revoke ingress rule on security group ' + securityGroupId + ' for port ' + port 
                + ' with cidrip ' + cidrIp);

    const commandStr = "sudo userdel -r " + randomUsername + ";"
             + " echo " + randomUsername + " expired baston account has been deleted";

    let ssm = new aws.SSM();

    let params = {
        DocumentName : 'AWS-RunShellScript',
        InstanceIds : [ instanceId ],
        Comment : 'delete local user account on linux managed instance',
        Parameters : { 'commands' : [ commandStr ] }
      };

    let responseMessage = '';
    ssm.sendCommand(params, function(err, data) {
       if (err) {
         responseMessage = 'attempt to remove user account ' + randomUsername + ' from target instance ' + instanceId 
                   + ' failed with error ' + err;
         console.error(responseMessage);
         reject(responseMessage);
       }
       else  {
        let revokeRequest = {
            CidrIp: cidrIp,
            FromPort: port,
            ToPort: port,
            IpProtocol: 'tcp',
            GroupId: securityGroupId
          };
         
          ec2.revokeSecurityGroupIngress(revokeRequest, function(err, data) {
            if (err) {
                responseMessage =  'attempt to revoke ingress rule on security group ' + securityGroupId + ' for port ' + port 
                + ' with cidrip ' + cidrIp + ' failed with error ' + err;
                console.error(responseMessage);
                reject(responseMessage);
            }
            else {
                responseMessage = 'Success attempt to remove user account ' + randomUsername 
                + ' from target instance ' + instanceId 
                + ' attempt to revoke ingress rule on security group ' + securityGroupId + ' for port ' + port 
                + ' with cidrip ' + cidrIp;
                resolve(responseMessage);
            } 
         });
       }
     });
  }
  catch(exp) {
    return reject('issue processing removal of ingress rule and local account for instance ' + instanceId + ' with error ' + exp);
  }
 });
}

//it is assumed that this will be called under Promise.all
//and we want to delete as many stacks as possible so the
//main promise in this method never calls reject only
//resolve
function evaluateStack(stack,event,context) {

  return new Promise(function(resolve, reject){
    try 
    {
      let params = { StackName: stack.StackId };

      //this should return just the indicated stack (non-promise based call)
      cloudformation.describeStacks(params, function(err, data) {
        let responseMessage = '';
        console.info('evaluate stack :: ' + stack.StackName);
        if (err) {
          responseMessage = 'error in describe stacks for stack :: ' + stack.StackName + ' error :: ' + err;
          resolve(responseMessage);
        }
        else {
           if (data.Stacks === null || data.Stacks.length === 0) {
             responseMessage = 'no matching stack for stack id ' + stack.StackId + ' nothing to evaluate this should have NOT happened';
             console.warn(responseMessage);
             resolve(responseMessage);
           }
           else {

              var describedStack = data.Stacks[0];
              if (helperStackHasOutputKeyWithValue(describedStack, 'BastionFlag', 'true')) {
                  let expireTimeStr = helperGetOutputKeyValue(describedStack, 'ExpireTime');
                  console.info('Bastion stack found ' + describedStack.StackName 
                           + ' with expiration time ' + expireTimeStr + ' current time is ' + (new Date()));
                  let expireTime = new Date(expireTimeStr);
                  if (expireTime <= (new Date())) {
                     //expiration time has passed
                     //so we have to delete the account on the managed instance
                     //and delete the stack (which spawned the Bastion instance)
                     if (helperStackHasOutputKeyWithValue(data.Stacks[0], 'BastionPlatform', 'linux')) {
                          isLinuxTarget(describedStack).then(function(data) {
                            deleteStack(describedStack).then(function(data) {
                              resolve(data);
                            }).catch(function(err) {
                              responseMessage = 'could not delete stack for Bastion instance ' + describedStack.StackName + ' with error ' + err;
                              console.error(responseMessage);
                              resolve(responseMessage);
                            });
                          }).catch(function(err) {
                           responseMessage = 'could not clean up ingress group, user account on target instance and delete the corresponding stack for ' + describedStack.StackName;
                           console.error(responseMessage);
                           resolve(responseMessage);
                          });
                     }
                     else { //windows target
                          isWindowsTarget(describedStack).then(function(data) {
                            deleteStack(describedStack).then(function(data) {
                              resolve(data);
                            }).catch(function(err) {
                              responseMessage = 'could not delete stack for Bastion instance ' + describedStack.StackName + ' with error ' + err;
                              console.error(responseMessage);
                              resolve(responseMessage);
                            });
                          }).catch(function(err) {
                            responseMessage = 'could not clean up ingress group, user account on target instance and delete the corresponding stack for ' + describedStack.StackName;
                            console.error(responseMessage);
                            resolve(responseMessage);
                          });
                     }
                  }
                  else {
                    console.info('Bastion stack ' + stack.StackName + ' has not yet expired');
                    resolve('Bastion stack ' + stack.StackName + ' has not yet expired');
                  } 
              }
              else {
                console.log('stack ' + stack.StackName + ' is not a Bastion stack');
                resolve('Bastion stack ' + stack.StackName + ' has not yet expired');
              }
           }
        }
     });
    }
    catch(exc) {
      console.error('issue evaulating stack for delete');
      resolve(exc);
    }
  });
}

//we are always going to resolve (not reject the promise)
function evaluateStacks(stacks, event, context) {

  return new Promise(function(resolve, reject) {
   
    try {

      let params = { StackStatusFilter: [ 'CREATE_COMPLETE' ] };
      cloudformation.listStacks(params).promise().then(function(data) { 

        let promises = [];
        for (let i in data.StackSummaries) {
          //we assume that all the evaluateStack promises 
          //resolve and not reject as we are using Promise.all
          //and we want to delete as many stacks as possible.
          promises.push(evaluateStack(data.StackSummaries[i],event,context));
        }
        
        return Promise.all(promises).then(function(data) {
           resolve('all stacks deleted');
        }).catch(function(err) {
           resolve('issue deleting all stacks :: ' + err);
        });
      }).catch(function(err) {
          resolve('issue listing all stacks :: ' + err + ' so no stacks were deleted');
      });
    }
    catch(exc) {
       resolve('issue evaluating stacks :: ' + exc);
    }
  });
}


exports.BastionTermExpired_handler = (event, context, callback) => {
 
     let params = { StackStatusFilter: [ 'CREATE_COMPLETE' ] };
     let responseMessage = '';

     console.log('BastionTermExpired_handler');

     //we assume evaluate stacks only resolves does not reject but
     //we keep the reject branch here just in case someone refactors
     evaluateStacks(event, context).then(function(data) {
       responseMessage = 'success from evaluate stacks';
       console.log(responseMessage);
       sendResponse(event, context, 'SUCCESS', responseMessage, {}).then(function(data) {
            context.callbackWaitsForEmptyEventLoop = false; 
            callback(null, data);
        }).catch(function(err) {
            context.callbackWaitsForEmptyEventLoop = false; 
            callback(new Error(err));
        });
     }).catch(function(err) {
       responseMessage = 'issue from evaluate stacks, error :: ' + err;
       console.error(responseMessage);
       sendResponse(event, context, 'SUCCESS', responseMessage, {}).then(function(data) {
            context.callbackWaitsForEmptyEventLoop = false; 
            callback(null, data);
        }).catch(function(err) {
            context.callbackWaitsForEmptyEventLoop = false; 
            callback(new Error(err));
        });
     });
};
