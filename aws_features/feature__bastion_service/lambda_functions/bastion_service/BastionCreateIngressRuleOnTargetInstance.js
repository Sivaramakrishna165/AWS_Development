'use strict';

var aws = require('aws-sdk');
var ec2 = new aws.EC2();

//This should be identifier unique to the custom resource vendor
let physicalResourceId = 'BastionCreateIngressRuleOnTargetInstance123456789abcdefg!#$';

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

function createIngressRule(port, cidrIp, instanceId, requestType) {
    
  return new Promise(function(resolve, reject){
    console.log('creating ingress rule port ' + port + ' cidrIp ' + cidrIp + ' for instance ' + instanceId);
    
    let responseMessage = '';
    
    try {
  
       //find the first security group associated with our instance
       //this will be the one we use to set our Ingress rule for the Bastion host 
       //to the target VM.
       //The API does not allow for the associating of a security group with an 
       //instance although we can create a security group and associate it with
       //a VPC.
       var params = { InstanceIds: [  instanceId ] };
       
       console.log('describe trying');
       let ec2 = new aws.EC2();
       ec2.describeInstances(params, function(err, data) {
    
       
       if (err) {
           responseMessage = 'could not find instance with instance id ' + instanceId + ' so we can not add an ingress rule for Bastion host access';
           console.error(responseMessage);
           reject(responseMessage); 
       }
       else {
        // Don't add any rule during delete
          if (requestType != 'Delete'){ 
            let securityGroupId = data.Reservations[0].Instances[0].SecurityGroups[0].GroupId;
            let ingressRule = {
                  CidrIp: cidrIp,
                  FromPort: port,
                  ToPort: port,
                  IpProtocol: 'tcp',
                  GroupId: securityGroupId
              };
              
              console.log('trying to add ingress rule ' + JSON.stringify(ingressRule));
              //add the rule
              ec2.authorizeSecurityGroupIngress(ingressRule, function(err, data) {
                 if (err) {
                    reject('issue setting ingress rule ' + err);
                 }
                 else {
                   responseMessage = 'ingress rule successfully added to security group with security group id ' + securityGroupId;
                    console.log('auth success ingress ' + JSON.stringify(data));
                    resolve({"SecurityGroupId" : securityGroupId});
                 }
              });
            }
          }  
       });
     }
     catch(exc) {
         responseMessage = 'error trying to add ingress rule ' + exc;
         console.error(responseMessage);
         reject(responseMessage);
     }
  });
}

exports.BastionCreateIngressRuleOnTargetInstance_handler = (event, context, callback) => {

    if (event.RequestType == 'Update' || event.RequestType == 'Delete') {
        sendResponse(event, context, 'SUCCESS', '', { "SecurityGroupId" : event.RequestType}).then(function(data) {
            context.callbackWaitsForEmptyEventLoop = false;
            callback(null, data);
        }).catch(function(err) {
            context.callbackWaitsForEmptyEventLoop = false;
            callback(new Error(err));
        });
    }

   
    let bastionPrivateIpCidr = event.ResourceProperties.BastionIpAddressCidr;
    let targetInstanceId = event.ResourceProperties.TargetInstanceId;
    let bastionPlatform = event.ResourceProperties.platform;
    
    let port = '';
    if (bastionPlatform == 'linux') {
        port = '22';
    }
    else { //assume windows
        port = '3389';
    }

    let requestType = event.RequestType;
    
    createIngressRule(port, bastionPrivateIpCidr, targetInstanceId, requestType).then(function(data) {
         console.log('response from create ingress rule' + JSON.stringify(data));
        
         //this contains the securityGroupId
         sendResponse(event, context, 'SUCCESS', 'created ingress rule', data).then(function(data) {
            context.callbackWaitsForEmptyEventLoop = false; 
            callback(null, data);
         }).catch(function(err) {
            context.callbackWaitsForEmptyEventLoop = false; 
            callback(new Error(err));
         });
    }).catch(function(err) {
         console.error('response from create ingress rule ' + JSON.stringify(err));
         sendResponse(event, context, 'FAILED', 'failed to create ingress rule for instance', {}).then(function(data) {
            context.callbackWaitsForEmptyEventLoop = false; 
            callback(new Error(err));
         }).catch(function(err) {
            context.callbackWaitsForEmptyEventLoop = false; 
            callback(new Error(err));
         });
    });
};
