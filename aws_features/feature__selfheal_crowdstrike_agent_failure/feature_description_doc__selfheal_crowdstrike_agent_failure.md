# Feature Description Document

**Feature Name: SelfhealCrowdstrikeFailure**

**Version: 10.0.0.4**

**StandardCreationBatch: 4**

**EnableFeature:**

- [X] **true**

- [ ] **false**

**Owner:**

- **Name: AWS Platform Engineering Team**

- **Email: awspe-all@dxc.com**

- **Other contact info: AWS Platform Engineering team, DXC Technology** 

**Purpose: Crowdstrike Agent failure self heal helps in fixing falcon agent failures notified in EC2 instances, this self heal checks for following diagnose area like Roles, CLI, falcon agent details & SSM Agent Failure & fix them automatically. Once the solution is able to diagnose & resolve it creates Information Event otherwise it create incidents in Service Now.** 

**Documentation: https://confluence.dxc.com/display/AWSMS/AWS+Self-Heal+Solution** 

**Settings:**

  - **Name:**

  - **Default value:**

  - **Allowed values:**

  - **Reaction to a change:**


  - **Name:**

  - **Default value:**

  - **Allowed values:**

  - **Reaction to a change:**


  - **Name:**

  - **Default value:**

  - **Allowed values:**

  - **Reaction to a change:**

**Scope overrides allowed:** 

- [ ] **Global**

- [ ] **Customer**

- [ ] **Organization Unit**

- [ ] **Account**

- [ ] **Region**

- [ ] **VPC**

- [ ] **Subnet**

- [ ] **Instance**

- [ ] **Volume**

- [ ] **Snapshot**

- [ ] **AMI**

- [ ] **Other:** *Specify*

**Feature enablement:**

- [X] **Feature enabled by default**

- [ ] **Allow disabling the feature per scope**

**Resources deployed:**
-
-
- 
{"mode":"full","isActive":false}
