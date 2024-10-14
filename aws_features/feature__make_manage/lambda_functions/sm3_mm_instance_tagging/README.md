# AWS-Offering-Capabilities - Feature-Make-Manage - STEP 3 StateMachineInstanceTagging

* Implemented via AWSPE-5779 and AWSPE-6010
* Acceptance Criteria:

** STEP 3 StateMachineInstanceTagging
   
   Here we are only performing the Instance Tagging related things and below are the tags which will be associated with the instance once this Lambda function will run from step function, and these tags will be fetched from the DynamoDB table named "featureParameterSet".

* Configure the instance as done in the Simple Workload Template User Data section (same as AWSPE-5672)
ApplyMonitoring
ApplyendpointProtection (install falcon agent)if no pre-existing instance profile exists, assign a DXC instance profile to the instance
apply hardening if possible.  If not possible, then hardening will be required in the next release.
Use the ParameterSet name passed in to this state, identify the values from the ParameterSet DynamoDB table and use to apply AWS Offering tags
"Name"
"InstanceName"
"Owner"
"Project"
"Application"
"Environment"
"Compliance"
"LeaseExpirationDate"
"Patch Group"
"EbsVolumeBackupLevel"
"BackupSchedule"
"RetentionPeriod"
"OSName"
"ApplyPatching"
"ApplyEndPointProtection"
"ApplyMonitoring"
"ApplyLogging"
"OSServiceLevel"
"OS-CIS-Compliance"

** Code WorkFlow 

* main_instance_tagging_hardening.py calls check_instance_running.py
* check_instance_running.py calls apply_instance_tagging.py
