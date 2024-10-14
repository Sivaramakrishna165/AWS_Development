var AWS = require('aws-sdk');
var backuputil = require('backuputil');
exports.handler = (event, context, callback) => {
  //console.log("Event:",event);
  console.log('Event:', JSON.stringify(event, null, 2));
  //console.log("Context:",context);
if(event['Records']){
processMessage(event['Records'],event);
}
}
function processMessage(messageList,event) {
  for(const index in messageList){
   
    processBackup(JSON.parse(messageList[index]['body']),messageList[index]['receiptHandle'],event);
  }
}

function processBackup(body, handle,event){
  var lam = new AWS.Lambda();
 // console.log("handle:",handle);
  //console.log("messageBody:",body);
  console.log("Backup Process Started for Instance:", body.instances.InstanceId);
  var EbsVolumeBackupLevel = 1;

    var backupAttempted = false;
    var optionalTag = body.backupSchedule; //  Tells which Instances to backup, if specified.
    // If this is a self invocation i.e. continueLambda()
    if (backuputil.isBlank(optionalTag)) {
        optionalTag = 'Default';
    }
    let scheduleMap = body.schedule;

        var instanceID = body.instances.InstanceId;
        var instance = body.instances;
        var backupInstance = false;
       
        var scheduleTag = 'Default';
        for (var t = 0; t < instance.Tags.length; t++) {
            if (instance.Tags[t].Key == 'EbsVolumeBackupLevel') {
                EbsVolumeBackupLevel = instance.Tags[t].Value;
            } else if (instance.Tags[t].Key == 'BackupSchedule') {
                scheduleTag = instance.Tags[t].Value; //  Save schedule name for validation...
                if (backuputil.isBlank(scheduleTag)) {
                    scheduleTag = 'Default';
                }
            }
            if (instance.Tags[t].Key == 'BackupAttempted') {
               backupAttempted = true;
            }
        }
        //console.log('Checking Instance: ', instanceID, ' which has scheudle tag as: ', scheduleTag, ' against: ', optionalTag);
        //  If this is a custom schedule, make sure the BackupSchedule matches:
        if (optionalTag && optionalTag != 'Default') {
            if (scheduleTag == optionalTag) {
                backupInstance = true;
            }
        } else {
            //  Default schedule - don't backup any Instances tagged with a custom schedule:
            if (scheduleTag == 'Default') {
                backupInstance = true;
            }
        }
        //  Validate that schedule for the Instance is valid:
        var hours = scheduleMap[scheduleTag];
        if (hours == null) {
            //  There's an instance with a backup schedule we don't recognize:
            console.log('The Instance ', instance.InstanceId, ' has an unrecognized backup schedule: ', scheduleTag);
            let message = 'The Instance ' + instance.InstanceId + ' has an unrecognized backup schedule: ' + scheduleTag;
            let msgData = {};
            msgData.instanceId = instance.InstanceId;
            //pushMessage(WarningMessage, message, msgData, null);
            //  Perform a backup if this is the standard schedule so we have at least a daily backup:
            if (!optionalTag || optionalTag === 'Default') {
                console.log('Performing backup of ', instance.InstanceId, ' for the missing schedule: ', scheduleTag);
                backupInstance = true;
            }
        }
        console.log("instanceID:" + instanceID + "|backupAttempted:" + backupAttempted + "|backupInstance:" +backupInstance);
        // If this instance is supposed to be backed up in this schedule and has not already been processed.
        if( backupAttempted == false && backupInstance == true){
          body.handle = handle;
          var backupMessage = 'Creating EbsVolumeBackupLevel ' +  EbsVolumeBackupLevel + ' backup for ' + instanceID;
          var params = { 
            FunctionName: "",
            InvocationType: "Event", 
            Payload: JSON.stringify(body), 
          }
        
          
          if( instance.State.Name == 'running' ){
            //tagInstanceAsAttempted(instanceID).then((result)=> {
            switch(EbsVolumeBackupLevel){
              case '0':
                console.log(" EbsVolumeBackupLevel set to 0, no backups done for " + instanceID);
                break;
              case '1':
               // numInstances++
               console.log("LevelOneBackup");
                params.FunctionName = "levelOneBackupLambda";
                //levelOneBackup(instance);
                break;
              case '2':
               // numInstances++
                if(instance.Platform == 'windows'){
                  console.log("LevelTwoWindowsBackup");
                  params.FunctionName = "levelTwoWindowsBackupLambda"
                  //levelTwoWindowsBackup(instance)
                } else {
                  console.log("LevelTwoLinuxBackup");
                  params.FunctionName = "levelTwoLinuxBackupLambda"
                 // levelTwoLinuxBackup(instance)
                }
                console.log(backupMessage);
                break;
              case '3':
                //goto case 4
              case '4':
                console.log('EbsVolumeBackupLevel ' +  EbsVolumeBackupLevel + ' not yet Implemented for ' + instanceID);
                //goto default
              default:
                console.log("No valid EbsVolumeBackupLevel set, default level 1 backup done for " + instanceID);
                //numInstances++
                console.log("LevelOneBackup");
                params.FunctionName = "levelOneBackupLambda";
                //levelOneBackup(instance);
                break;
            }
          //}).catch((error) => console.log(error));
            // sleep(lambdaWaitTime)
            lam.invoke(params, function(err, data) {
              if (err) console.log(err, err.stack);
              else     console.log(params.FunctionName+'Lambda backupHandler Invoked');
            });
          } else {
            if(EbsVolumeBackupLevel > 0){
              if(instance.State.Name == 'stopped' || instance.State.Name == 'stopping'){
                console.log('Instance is in ' + instance.State.Name + ' state, doing level 1 backup for ' + instanceID + '.');
                //numInstances++;
                params.FunctionName = "levelOneBackupLambda";
                //levelOneBackup(instance);
                console.log("LevelOneBackup");
                backuputil.tagInstanceAsAttempted(instanceID).then((result) => {
                  console.log('SUCCESS');
                  lam.invoke(params, function(err, data) {
                    if (err) 
                    {
                      console.log('Error')
                      console.log(err, err.stack);
                    }
                    else{     
                      console.log('No Error');
                      console.log(params.FunctionName+'Lambda backupHandler Invoked');
                      
                    }
                  })
                }).catch((error)=> console.log(error));
                console.log(backupMessage);
                // sleep(lambdaWaitTime);
              }
            }
          }
        }
        // //if block ending for backupAttempted
       // var msgtoDelete = messagelistMap.get(instanceID);
        console.log('instanceID:',instanceID);
       // console.log('msgtoDelete:',msgtoDelete);
        //deleteMessage(msgtoDelete);
        // //waiting for 2secs
        // sleep(1000 * 2);
        
  // }

}
