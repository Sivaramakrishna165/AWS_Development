# AWS-Offering-Capabilities - Feature-Make-Manage - STEP 4 StateMachineInstancePackageInstall

* Implemented via AWSPE-5779 and AWSPE-6010
* Acceptance Criteria:

** STEP 4 StateMachineInstancePackageInstall

* Statemachine Lambda splitup implemented via [AWSPE-6391]

** Code WorkFlow 

* dxc_mm_sm4_install_packages.py.py calls boto_helper.py
* boto_helper.py calls install_awscli.py and install_extra_package.py
