# AWS-Offering-Capabilities - Feature-Make-Manage - STEP 5 StateMachineInstallCloudwatch

* Implemented via AWSPE-5779 and AWSPE-6010
* Acceptance Criteria:

** STEP 5 StateMachineInstallCloudwatch

* Configure the instance as done in the Simple Workload Template User Data section (same as AWSPE-5672)
* ApplyMonitoring - have Cloudwatch agent installed.

* Statemachine Lambda splitup implemented via [AWSPE-6294]

** Code WorkFlow 

* apply_instance_monitoring calls cloudwatch_command_os_type.py
