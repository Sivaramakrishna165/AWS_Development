#appDisplayName = CoRECM Deployment
#appTypeName = CoRECM Source Setup Module
#CoREVersion = CoRE for W2K16 v1.0.4

#Powershell version prerequisite -  the below comment automatically verifies the ps version
#requires -Version 3.0

#region Author and Change History
#Author  : Chris Yantha
#Date    : 11-07-2016
#Version : 1.0
#Version History:
<#
    v1.1 - umesh thakur - 05-dec-2017
        - branded for CoRE, updated function names to match their changed names and using function to write common header
    v1.2 - umesh thakur - 08-mar-2018
         - updated team sharepoint portal, email and #CoREVersion (at top of the script)
	v1.3 - Hari 29 June 2018
		 - Updated Incorrect Variable assigment for repositorylocation in the section main where the code checks for existing repository and adjusted New-Item Command lets
	v1.4 - Hari 5 Sept
		 - $env:temp should return full path in -Update section of code
#>

#endregion

<#
.SYNOPSIS
Script will Deploy the CoRECM Tool

.DESCRIPTION
This script is intended to deploy the CoRECM toolset.

.PARAMETER LogFilePath - The Location for log file.

.PARAMETER wcSourcePath - Source Path for CoRECM zip package

.PARAMETER wcTargetPath - Target Path where WC has to be stored by default C:\SUPPORT

.PARAMETER ReInstall - Remove all traces of exiisting CoRECM and deploy a new version

.PARAMETER Revert - Unisntall CoRECM

.PARAMETER Update - Perform Update of scripts in the local CoRECM Source from the package.

.EXAMPLE
.\SETUP.PS1 -LogFilePath C:\SUPPORT\LOGS\<LogFileName>.Log 
    
.EXAMPLE
.\SETUP.PS1 -wcSourcePath C:\SUPPORT\WC.ZIP

.EXAMPLE
.\SETUP.PS1 -ReInstall

.EXAMPLE
.\SETUP.PS1 -Revert

.EXAMPLE
.\SETUP.PS1 -Update
    
.NOTES
CoRECM tool is designed to analyze a Windows Server OS compliance against DXC Global standards.This script is intended to deploy the CoRECM toolset.
- Exit 0 = Success
- Exit 1 = Failure
- Exit 2 = Unable to setup C:\SUPPORT
- Exit 3 = Unable to unzip CoRECM zip
- Exit 4 = CoRECM package is missing
- Exit 5 = CoRECM Source is detected in the build.Error trying to rename the existing source.
- Exit 6 = CoRECM Uninstall process failed. 
- Exit 10 = Unable to create Log Files. function Set-CodeModulesLog
- Exit 11 = Script not executed in Admin Approval Mode
- Exit 12 = AutoUpdater Script Exited with Error
- Exit 14 = AutoUpdater didnt run because it was not able detect existing CoRECM version
- Exit 15 = WCRepo doesnt have write acess
- Exit 16 = Error Creating wcRepo
- Exit 17 = Existing CoRECM Local Source Detected
- Exit 18 = CoRECM is not Installed

.LINK
https://dxcportal.sharepoint.com/sites/Platformx86SOE/SitePages/Home.aspx

platform_x86_CoRE@dxc.com

#>

[CmdletBinding(DefaultParameterSetName="CoREModuleParams")]
Param(
$LogFilePath = "$env:SystemDrive\SUPPORT\LOGS\CoRECMSetup.Log", # Mandatory Field
[Parameter(ParameterSetName="CoREModuleParams")]
[Parameter(ParameterSetName="repo")]
[Parameter(ParameterSetName="Update")]
[Parameter(ParameterSetName="ReInstall")]
[ValidateScript({([System.IO.File]::Exists((resolve-path $_).path)) -and $_.trim().split(".")[-1] -eq 'zip'})] $wcSourcePath = "$psScriptRoot\CoRECM.zip",
[Parameter(ParameterSetName="CoREModuleParams")]$wcTargetFolder = "$env:SystemDrive\SUPPORT",
[Parameter(ParameterSetName="repo")] [Switch] $Revert,
[Parameter(ParameterSetName="ReInstall")][Switch] $ReInstall,
[Parameter(ParameterSetName="Update")][Switch] $Update,
[Parameter(ParameterSetName="repo")]
[ValidateScript({(([uri]($_)).IsUNC)})]$wcRepositoryPath #repo Path should be empty and should be a UNC
)

#region Common Functions
#Function to Set-Log
Function Set-CodeModulesLog($LogFilePath) {
    Try {
        if (!(Test-Path $LogFilePath)) {
            New-Item $LogFilePath -Type File -Force | Out-Null;
        }
        $Script:LogPath = $LogFilePath
    }
    Catch {
        Exit 10; #Exit 10  failed
    }

}

#Function to Write messages to the log file that was set using Set-CodeModulesLog function
Function Write-CodeModulesLog($Message) { 
    
    if($Message -ne $NULL) {
        Write-Verbose $Message -Verbose;

        if(Test-Path $Script:LogPath) {
            Add-Content -Path $Script:LogPath -Value "$(get-date -format "MM/dd/yyyy hh:mm:ss") : $Message";
        }
    }

}

#Function to Verify Admin approval Mode - whether script is launched using Administrative credentials
Function Test-AdminApprovalMode() {
    return ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator");
}

# This function will return whether current server provisioning method is CoRE build or CoRE modules
Function Get-InstallMode{
    If ($psScriptRoot.ToUpper().contains("SUPPORT") -and $psScriptRoot.ToUpper().contains("BOOT") `
        -and $psScriptRoot.ToUpper().contains("_APPS") -and (Test-Path -Path "$env:systemdrive\SUPPORT\buildconfig.xml")){
        Return "Build" #Detected as running within the original Windows Server CoRE Install process
    }
    Else {
        Return "Modular" #Detected as running as a standalone modue
     }
}

# If module need to set branding information in Registry, this function can be used

#endregion

#region Functions copied from wcManagement Console
#Function to check whether repo already exists in wmc Config File or share
Function Test-WMCRepoExists {
Param (
$RepositoryLocation,
[Switch]$WriteAccess
)
    try {
        #check to see a connection can be established to RepositoryLocation
        if((Test-Path $RepositoryLocation) -eq $false) { return "Error : Unable to connect to specified repo Location: $RepositoryLocation" }

		#check to see if we have write access  to the share
        if($WriteAccess.IsPresent) {
            $wcTime = (date).ToString('MMddyyhhmmss');
            New-Item -ItemType File -Path "$RepositoryLocation\wcrepowatest_$wcTime.txt" -ErrorAction SilentlyContinue | Out-Null
            if((Test-Path "$RepositoryLocation\wcrepowatest_$wcTime.txt") -eq $false) {
                return "Error : Unable to create repository on the specified Repository Location.Please check the access to repository location"
            }
			else {
				Remove-Item "$RepositoryLocation\wcrepowatest_$wcTime.txt" -Force
			}
        }

        #else return success
        return "Success"
    }
    catch {
        return "Error : $($_.Exception.Message)"
    }  
}

#Function to create a new repository
function New-WMCRepository { 

Param (
    [Parameter(Mandatory=$true)][String]$RepositoryLocation,
    $RepoLocationStructure = @("Inventory","Inventory\template","Reports","Logs")
    )
    try {
        #create the repository folder structure   
        foreach($RepositoryDirectory in $RepoLocationStructure) {
            if(!(Test-Path "$RepositoryLocation\$RepositoryName\$RepositoryDirectory")) {
                New-Item -ItemType Directory -Path "$RepositoryLocation\$RepositoryName\$RepositoryDirectory" -Force | Out-Null
            }
        }
        #create structure for Inventory File
        $repoValue =@"
            {
				"Name":  "",
				"Groups":  [
							  
						   ],
				"Hosts":  [
							  
						  ],
				"CoRECMRepo":  "",
				"ReadOnly":  ""
			}
"@
		$reportValue =@"
            {
				"ReportHistory":  [
							  
						   ]
			}
"@
        #create Inventory File     
        if(!(Test-Path "$RepositoryLocation\$RepositoryName\Inventory\template\wcInventory.JSON")) { #skip in case of existing repo
            ConvertFrom-JSON $repoValue | Convertto-JSON | Out-File "$RepositoryLocation\$RepositoryName\Inventory\template\wcInventory.JSON"
			ConvertFrom-JSON $reportValue | Convertto-JSON | Out-File "$RepositoryLocation\$RepositoryName\Inventory\template\wcReportHistory.JSON"
        }
		return "Success"
    }
    catch {
        return "Error : $($_.Exception.Message)"
    }
}
#endregion
#region Functions related to this script
#Function to create the WC Source Paths -folders for Logging etc
Function Set-WCSource($SourcePath) {
    try {
        if(!(test-Path $SourcePath)) {
            Write-CodeModulesLog -Message "Creating Directory : $SourcePath"
            New-Item -ItemType Directory -Path $SourcePath -Force | Out-Null;
        }
    }
    catch {
        Write-CodeModulesLog -Message $_.Exception.Message
        Exit 4;
    }
}
Function Expand-ZIPFile($sourceFile,$targetFolder) {
	try {
		Write-CodeModulesLog -Message "Extracting $sourceFile to $targetFolder"
		[System.Reflection.Assembly]::LoadWithPartialName('System.IO.Compression.FileSystem') | Out-Null
		[System.IO.Compression.ZipFile]::ExtractToDirectory($sourceFile, $targetFolder)
	}
	catch {
		Write-CodeModulesLog -Message $_.Exception.Message
		Exit 3;
	}
}

#WC Registry Branding
Function Set-WCBranding {    
    param(
        $CoRERegPath = "HKLM:\SOFTWARE\DXC\CoRECM", # default CoRE registry location
        $BrandingName, # "GlobalVersion.
        $BrandingValue # 1.1
    )

    # if CoRE registry location doesn't exist then create it
    if(!(Test-Path $CoRERegPath)){New-Item $CoRERegPath -Force | Out-Null}

    #Append Script InstallMode with Branding
    Set-ItemProperty -Path $CoRERegPath -Name $BrandingName -Value $BrandingValue

}

#Test existance of Mandaory Files and WC Source
Function Test-WCSource($SourcePath,$wcPackagePath) {
    try {
	
		#check for any version of wc installed
		$wcExistingSource = (Get-ItemProperty HKLM:\SOFTWARE\DXC\CoRECM -Name InstallFolder -ErrorAction SilentlyContinue).InstallFolder
		if($wcExistingSource) {
			if(Test-Path $wcExistingSource) {
				Write-CodeModulesLog "An existing CoRECM Source detected at $wcExistingSource .You may wish to uninstall using -revert parameter and try installation again"
				exit 17;
			}
		}
        
		#check for wc package
		if(!(Test-Path $wcPackagePath))  {        
            Write-CodeModulesLog "CoRECM package is missing.Exiting with return code = 4"
            Exit 4;
        }
		elseif((Test-Path "$SourcePath\wcremediation.ps1") -and (Test-Path "$SourcePath\modules\wcUtils.psm1"))  {        
            Write-CodeModulesLog "CoRECM source already exists at $SourcePath.You will need to use the reinstall parameter to remove existing package and install a new package"
            Exit 4;
        }
        elseif(Test-Path $SourcePath) { # CoRECM 2.2 or older version
           Write-CodeModulesLog -Message "$SourcePath detected in the Build."
           Write-CodeModulesLog -Message "Renaming the existing CoRECM Source to $($SourcePath)_OLD";
           $FolderName = ($SourcePath.Split("\"))[-1]
           Rename-Item -Path $SourcePath -NewName "$($FolderName)_OLD"
        }
    }
    catch {
        Write-CodeModulesLog -Message $_.Exception.Message
        Exit 5;
    }
}
#Test existance of Mandaory Files and WC Source
Function Remove-CoRECM{
param(
	$SourcePath,
	$RegPath = "HKLM:SOFTWARE\DXC\CoRECM",
    [Switch]$SkipRegClean
	) 
    try {
		Write-CodeModulesLog -Message "CoRECM Path : $SourcePath"
		if($SourcePath){
			if(Test-Path "$SourcePath\CoRECM") {
				Write-CodeModulesLog -Message "Deleting CoRECM Source Folder : $SourcePath"

				#Check whether its a valid WC Source
				if((Test-Path "$SourcePath\CoRECM\wcremediation.ps1") -and (Test-Path "$SourcePath\CoRECM\modules\wcUtils.psm1")) {
					#remove WC Source Folder
					Remove-Item -Path "$SourcePath\CoRECM" -Recurse -Force
				}
			}
			else {
				Write-CodeModulesLog -Message "CoRECM Source Folder : $SourcePath doesn't exists"
			}
		}
		
		if(!($SkipRegClean.IsPresent)) {
			Write-CodeModulesLog -Message "Cleaning CoRECM Registry : $RegPath"
			#cleanup Registry
			if(Test-Path $RegPath) {
				Remove-Item $RegPath -Recurse -Force;
			}
		}
	}
	catch {
		Write-CodeModulesLog -Message $_.Exception.Message
        Exit 6; #Remove process failed.
	}
}
Function Set-wcTempPath($wcSourcePath,$wcTempPath) {
    try {

        Write-CodeModulesLog -Message "Creating Team Path $wcTempPath"

        if(Test-Path $wcTempPath) { Remove-Item "$wcTempPath" -Force -Recurse }
        New-Item -ItemType Directory -Path "$wcTempPath" -Force  | Out-Null

        #Unzip WC ZIP File       
        Write-CodeModulesLog -Message "Unzip CoRECM Source to $wcTempPath"
        Expand-ZIPFile -sourceFile $wcSourcePath -targetFolder "$wcTempPath"

        #Update the autoConfig XML asking not to replace the ticonfig.xml
        $autoConfigPath = "$wcTempPath\CoRECM\Config\wcmautoupdateclientconfig.xml"

        [xml]$autoConfigXML = Get-Content $autoConfigPath
        $tiConfig = $autoConfigXML.CreateElement("File")
        $tiConfig.InnerText = "tiConfig.xml"
        $autoConfigXML.WCMAutoUpdateConfig.Settings.ExcludeList.AppendChild($tiConfig) | Out-Null;

        #Update Repository Path
        $autoConfigXML.WCMAutoUpdateConfig.RepositoryLocation.Config.SetAttribute("Location",$wcTempPath)
        $autoConfigXML.Save($autoConfigPath);

        #return AutoConfig xml
        return $autoConfigPath;

    }
    catch {
        Write-CodeModulesLog -Message $_.Exception.Message
        return "Error"
    }
}
#endregion

#region load PS common module else exit if failed
# check for existence of import commn module and import it if exists
$cModulePath = "$PSScriptRoot\SMCommon.psm1"
if((Test-Path $cModulePath)) {
    Import-Module -Name $cModulePath -Force
}
else { # module not found
    write-error "A required module $cModulePath was not found, aborting script"
    exit 20
}
#endregion common module load, OS install mode detection and set log file

#region 
#Validate Admin Approval Mode
if(!(Test-AdminApprovalMode)) { Exit 11;}

#change verbose message background
((Get-Host).PrivateData).VerboseBackgroundColor =($host.UI.RawUI).BackGroundColor;
#endregion

#Set LogPath
Set-CodeModulesLog -LogFilePath $LogFilePath

#Identify build provisioning method - CoREBuild or CoREModularized 
$InstallMode = Get-InstallMode

#Assign BrandHeader for this script
Write-CodeModuleInfo -ModuleName "CoRECM Deployment"

#change verbose message background
((Get-Host).PrivateData).VerboseBackgroundColor =($host.UI.RawUI).BackGroundColor;
#endregion


if($wcRepositoryPath) { #Actions Specific to WCRepo
	$wcTargetFolder = $wcRepositoryPath #Set Target Folder to CoRECM Repository
    Write-CodeModulesLog "Repository : $wcRepositoryPath"
    
    $Result = Test-WMCRepoExists -RepositoryLocation $wcRepositoryPath -WriteAccess ; #Test Repository for write Access
    Write-CodeModulesLog "Testing write Access to Repository : $Result"

	if($Result -eq "Success") {

	    if(!($Revert.IsPresent)) { #Setup CoRECM Repository
						        
			#check if existing repository
			#updated by Hari 29 June 2018 - changed incorrect variable $repositorylocation to $wcrepositorypath
			if(Test-Path "$wcRepositoryPath\CoRECM") { 
				Write-CodeModulesLog "Repository already exists at $wcRepositoryPath\CoRECM"
				exit 192;
			} 
		
            #Create Repository
			$Result = New-WMCRepository -RepositoryLocation $wcRepositoryPath
            Write-CodeModulesLog "Creating and setting up Repository : $Result"

			#Return Error if there were issues accesing repository
            if($Result -ne "Success") { 
				exit 16;
			}
            else {
                Expand-ZIPFile -sourceFile $wcSourcePath -targetFolder $wcTargetFolder #extract wc
                Write-CodeModulesLog "Succesfully Extracted CoRECM in Repository"
                Exit 0;
            }
		}
        elseif($Revert.IsPresent) { #clean up repo
            Write-CodeModulesLog "Cleaning up Repository : $Result"
            Remove-CoRECM -SourcePath $wcTargetFolder -SkipRegClean;
            exit 0;
        }
		else { #Unknown Parameter
			Exit 128;
		}
	}
    else {
        exit 15;
    }
}
elseif($Update.IsPresent) { #This feature is to  local source
 
    $wcTempPath = "$((Get-Item $env:Temp).FullName)\WcRepo"
    $wcInstallPath = (Get-ItemProperty HKLM:\SOFTWARE\DXC\CoRECM -Name InstallFolder -ErrorAction SilentlyContinue).InstallFolder

    if($wcInstallPath) {

        $AutoConfigXML = Set-wcTempPath -wcSourcePath $wcSourcePath -wcTempPath $wcTempPath

        if($AutoConfigXML -ne "Error") {
        
            Write-CodeModulesLog "wcInstallPath : $wcInstallPath"

            #Launch Auto Update Command with autoConfigXML
            Write-CodeModulesLog "Launching Auto Updater Script"
            $wcUpdaterReturn =  Invoke-Expression "$wcInstallPath\wcAutoUpdate.ps1 -autoConfigXML $AutoConfigXML";

            #Remove temp Path
            Remove-Item $wcTempPath -Recurse -Force;

            Write-CodeModulesLog "ExitCode : $($wcUpdaterReturn.ExitCode)"
            Write-CodeModulesLog "Message : $($wcUpdaterReturn.Message)";
            Write-CodeModulesLog "Status : $($wcUpdaterReturn.Status)";
            exit $($wcUpdaterReturn.ExitCode);

        }
        else {
            exit 12; #Auto Updater Script Error
        }
    }
    else {
        Write-CodeModulesLog "Existing CoRECM source is not detected.Skipping Update Process"
        exit 14;
    }
      
}
elseif($Revert.IsPresent -or $ReInstall.IsPresent) { #Local revert and reinstall 
    
    #Identoify Current WC Location for Reinstall
    $wcTargetFolder = (Get-ItemProperty HKLM:\SOFTWARE\DXC\CoRECM -Name InstallFolder -ErrorAction SilentlyContinue).InstallFolder
	
	if(!($wcTargetFolder)) { 
		if($ReInstall.IsPresent) {
			Write-CodeModulesLog "CoRECM is not Installed, you may wish to use -install parameter to perform a fresh install";
			Exit 18;
		}
	}
	elseif(!(Test-Path $wcTargetFolder)) {Write-CodeModulesLog "CoRECM package doesnt exists at $wcTargetFolder" }
	else{ 
		$wcIndex = ($wcTargetFolder.Split("\")[-1]).Length
		$wcTargetFolder = $wcTargetFolder.SubString(0,$wcTargetFolder.Length - ($wcIndex + 1));
	}
	
	#Cleanup CoRECM and Exit
	Remove-CoRECM -SourcePath $wcTargetFolder

	Write-CodeModulesLog "CoRECM successfully un-installed.Exiting with return code = 0"
	
	#If its ReInstall proceed with Install procedures ,if its revert/uninstall then skip
	if($Revert.IsPresent)  { Exit 0; } #Exiting the script here
    
    
}

#Section Fresh Install - Applicable for Reinstall or Fresh Install

#region Setup wcSource
#Check for existance of C:\Support\CoRECM and reaname if needed.
Test-WCSource -SourcePath "$wcTargetFolder\CoRECM" -wcPackagePath $wcSourcePath
#Setup CoRECM Source
Set-WCSource -SourcePath $wcTargetFolder
#Unzip WC ZIP File
Expand-ZIPFile -sourceFile $wcSourcePath -targetFolder $wcTargetFolder
#endregion

#region Branding
if(!($wcRepositoryPath)) { #Dont Update Registry Key if you are creating a repository
    [xml]$xml = get-content "$wcTargetFolder\CoRECM\Config\wcConfig.xml"
    Write-CodeModulesLog "Updating CoRECM Registry Branding"
    Set-WCBranding -BrandingName "GlobalVersion" -BrandingValue $xml.CoRECM.version
    Set-WCBranding -BrandingName "InstallDate" -BrandingValue $(Get-Date).ToString('MM-dd-yy hh:mm:ss')
	Set-WCBranding -BrandingName "InstallFolder" -BrandingValue "$wcTargetFolder\CoRECM"
}
#endregion

Write-CodeModulesLog "CoRECM Setup Module successfully completed execution.Exiting with return code = 0"
Exit 0

#endregion Main


