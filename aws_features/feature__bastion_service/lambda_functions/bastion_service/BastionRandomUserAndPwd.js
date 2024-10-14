'use strict';

//Used for username and password generation
const randomCharacterBank = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXY';
const randomNumberBank = '0123456789';
const randomSpecBank = '#!_';

const aws = require('aws-sdk');
const ssm = new aws.SSM();

//This should be identifier unique to the custom resource vendor
let physicalResourceId = 'BastionRandomUserAndPwd123456789abcdefg!#$';

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

function getRandomCharacterInString(inStr, numChars) {

    let resultString = '';
    for (let i = 0; i < numChars; i++) {
       resultString += inStr[Math.floor(Math.random()*(inStr.length))];
    }
    return resultString;
}

function generateRandomPassword() {
    let password = '';
    password += getRandomCharacterInString(randomCharacterBank, 4);
    password += getRandomCharacterInString(randomSpecBank, 1);
    password += getRandomCharacterInString(randomNumberBank, 3);
    password += getRandomCharacterInString(randomCharacterBank, 2);
    return password;
}

function generateRandomUsername() {
    let username = '';
    username += getRandomCharacterInString(randomCharacterBank, 4);
    username += getRandomCharacterInString(randomNumberBank, 4);
    return username;
}

exports.BastionRandomUserAndPwd_handler = (event, context, callback) => {

    console.info('creating random user and password for Bastion host');
 
    //we just handle Create Events
    if (event.RequestType == 'Delete' || event.RequestType == 'Update') {
        
        sendResponse(event, context, 'SUCCESS', '', {}).then(function(data) {
            context.callbackWaitsForEmptyEventLoop = false; 
            callback(null, data);
        }).catch(function(err) {
            context.callbackWaitsForEmptyEventLoop = false; 
            callback(new Error(err));
        });
    }
    
    //It would be better if this was set in a management function
    //with restricted roles and not hard coded
    try {
      const randomUsername = generateRandomUsername();
      const randomPassword = generateRandomPassword();

      //get from Cloud formation template
      let expirationIntervalMinutes = 60;
      
      let expireTime = new Date();
      expireTime = expireTime.setMinutes(expireTime.getMinutes()+expirationIntervalMinutes);
      expireTime = new Date(expireTime);
      
      let requestUser = 'unknown';
      if (event.ResourceProperties && event.ResourceProperties.Requestor) {
            requestUser = event.ResourceProperties.Requestor;
      }
      
      let responseData = {
            'random_pwd': randomPassword,
            'random_username': randomUsername,
            'request_user': requestUser,
            'expire_time': expireTime
        };
        console.log('result ' + JSON.stringify(responseData));        
        sendResponse(event, context, 'SUCCESS', 'Successfull call', responseData).then(function(data) {
            context.callbackWaitsForEmptyEventLoop = false; 
            callback(null, responseData);
        }).catch(function(err) {
            context.callbackWaitsForEmptyEventLoop = false; 
            callback(new Error(err));
        });
    }
    catch(exc) {
        
        let excMessage = 'exception creating username and password :: ' + exc;
        sendResponse(event, context, 'FAILED', excMessage, {}).then(function(data) {
            context.callbackWaitsForEmptyEventLoop = false; 
            callback(new Error(excMessage));
        }).catch(function(err) {
            context.callbackWaitsForEmptyEventLoop = false; 
            callback(new Error(excMessage));
        });
    }
};
