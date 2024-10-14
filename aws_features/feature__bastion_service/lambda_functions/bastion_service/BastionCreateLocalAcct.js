'use strict';

const aws = require('aws-sdk');

//This should be identifier unique to the custom resource vendor
const physicalResourceId = 'BastionCreateLocalAcct123456789abcdefg!#$';
    
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

//returns a promise
function createLinuxUserAccount(event, context) {

return new Promise(function(resolve, reject){

  try {
    const randomUsername = event.ResourceProperties.random_username;
    const randomPassword = event.ResourceProperties.random_pwd;
    const requestUser = event.ResourceProperties.request_user;
    const expireTime = event.ResourceProperties.expire_time;
    const instanceId = event.ResourceProperties.instance_id;

    const commandStr = 'sudo useradd -m -s /bin/bash ' 
          + randomUsername + ';'
          + ' echo ' + randomUsername + ':' 
          + randomPassword + ' | sudo chpasswd;' 
          + ' echo random_user: ' + randomUsername
          + ' created at request of: ' + requestUser + ';';

    let ssm = new aws.SSM();

    let params = {
        DocumentName : 'AWS-RunShellScript',
        InstanceIds : [ instanceId ],
        Comment : 'create local user account on bastion linux instance stack',
        Parameters : { 'commands' : [ commandStr ] }
      };

    ssm.sendCommand(params, function(err, data) {
       if (err) reject(err);
       else     resolve(data);
     });
  }
  catch(exp) {
    return reject(exp);
  }
 });
}

//returns a promise
function createWindowsUserAccount(event, context) {

return new Promise(function(resolve, reject){

  try {
    const randomUsername = event.ResourceProperties.random_username;
    const randomPassword = event.ResourceProperties.random_pwd;
    const requestUser = event.ResourceProperties.request_user;
    const expireTime = event.ResourceProperties.expire_time;
    const instanceId = event.ResourceProperties.instance_id;

    const commandStr =
        '$User = "' + randomUsername + '"\n'
        + '$Computer = $env:COMPUTERNAME \n'
        + '$GroupName = "Administrators" \n'
        + '$ADSI = [ADSI]("WinNT://$Computer") \n'
        + '$HelpDesk=$ADSI.Create("User",$User) \n'
        + '$HelpDesk.SetPassword("' + randomPassword + '") \n'
        + '$HelpDesk.SetInfo() \n'
        + '$HelpDesk.Put("Description","CSC Support Local Account") \n'
        + '$HelpDesk.SetInfo() \n'
        + '$Group = $ADSI.Children.Find($GroupName, "group") \n'
        + '$Group.Add(("WinNT://$computer/$user")) \n';

    let ssm = new aws.SSM();

    let params = {
        DocumentName : 'AWS-RunPowerShellScript',
        InstanceIds : [ instanceId ],
        Comment : 'create local user account on bastion windows instance stack',
        Parameters : { 'commands' : [ commandStr ] }
      };

    ssm.sendCommand(params, function(err, data) {
       if (err) reject(err);
       else     resolve(data);
     });
  }
  catch(exp) {
      return reject(exp);
  }
 });
}

exports.BastionCreateLocalAcct_handler = (event, context, callback) => {

    //we just handle Create events
    if (event.RequestType == 'Delete' || event.RequestType == 'Update') {
        sendResponse(event, context, 'SUCCESS', '', {}).then(function(data) {
            context.callbackWaitsForEmptyEventLoop = false; 
            callback(null, data);
        }).catch(function(err) {
            context.callbackWaitsForEmptyEventLoop = false; 
            callback(new Error(err));
        });
    }

    try {

      if (event.ResourceProperties && event.ResourceProperties.platform && (event.ResourceProperties.platform == 'linux' || event.ResourceProperties.platform == 'windows')) {
         if (event.ResourceProperties.platform == 'linux') {
            createLinuxUserAccount(event, context).then(function(data) {
              sendResponse(event, context, 'SUCCESS', '', {}).then(function(data) {
                 context.callbackWaitsForEmptyEventLoop = false; 
                 callback(null, data);
              }).catch(function(err) {
                 context.callbackWaitsForEmptyEventLoop = false; 
                 callback(new Error(err));
              });
            }).catch(function(err) {
              sendResponse(event, context, 'FAILED', '', {}).then(function(data) {
                 context.callbackWaitsForEmptyEventLoop = false; 
                 callback(new Error(err));
              }).catch(function(err) {
                 context.callbackWaitsForEmptyEventLoop = false; 
                 callback(new Error(err));
              });
            });
         }
         else {
            createWindowsUserAccount(event, context).then(function(data) {
              sendResponse(event, context, 'SUCCESS', '', {}).then(function(data) {
                 context.callbackWaitsForEmptyEventLoop = false; 
                 callback(null, data);
              }).catch(function(err) {
                 context.callbackWaitsForEmptyEventLoop = false; 
                 callback(new Error(err));
              });
            }).catch(function(err) {
              sendResponse(event, context, 'FAILED', '', {}).then(function(data) {
                 context.callbackWaitsForEmptyEventLoop = false; 
                 callback(new Error(err));
              }).catch(function(err) {
                 context.callbackWaitsForEmptyEventLoop = false; 
                 callback(new Error(err));
              });
            });
         } 
       }
       else {

         sendResponse(event, context, 'FAILED', 'event.ResourceProperties.platform must be set to linux or windows', {}).then(function(data) {
            context.callbackWaitsForEmptyEventLoop = false; 
            callback(null, data);
          }).catch(function(err) {
            context.callbackWaitsForEmptyEventLoop = false; 
            callback(new Error(err));
          });
       }
    }
    catch(excp) {
      let responseStatusReason = 'exception creating Bastion local user account :: ' + excp;
      sendResponse(event, context, 'FAILED', responseStatusReason, {}).then(function(data) {
         context.callbackWaitsForEmptyEventLoop = false; 
         callback(new Error(responseStatusReason));
      }).catch(function(err) {
         context.callbackWaitsForEmptyEventLoop = false; 
         callback(new Error(responseStatusReason));
      });
    }
};
