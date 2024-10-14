# Powershell version prerequisite -  the below comment automatically verifies the ps version
#requires -Version 3.0

# Module Name : SMCommon.psm1
# Purpose : This module contains common functions to be leveraged by all other CoRE Modules installer

#region Version History:
<#
    v1.0 - umesh thakur
        - branded for CoRE and added function to write header info for each module
#>
#endregion Version History

# for consolehost, make verbose background color same as host background color, makes it more readable
if($host.Name -eq 'ConsoleHost') {
    $host.PrivateData.VerboseBackgroundColor = $host.ui.RawUI.BackgroundColor
    $host.PrivateData.VerboseForegroundColor = "yellow" # cyan, to match ISE
}

# This function sets log file path and creates the log file if it doesn't exist
# -----------------------------------------------------------------------------
Function Set-CodeModulesLog($LogFilePath) {
    Try {
        if (-not (Test-Path $LogFilePath)) {
            New-Item $LogFilePath -Type File -Force | Out-Null
        }
        $Script:LogPath = $LogFilePath
    }
    Catch {
        10 #Exit 10  failed
    }
}

# Function to Write messages to the log file
# ------------------------------------------
Function Write-CodeModulesLog($Message) { 
    if($Message -ne $NULL) {
        Write-Verbose -Message $Message -Verbose # write all log messages as verbose
        if($script:LogPath -eq $NULL -or ($script:LogPath).length -eq 0) {
            return # no log file given, skip writing to log file
        }
        # if valid log file then write to log file as well
        if(Test-Path $Script:LogPath) {
            Add-Content -Path $Script:LogPath -Value "[$(get-date -format "MM/dd/yyyy hh:mm:ss")] $Message"
        }
    }
}

# ----------------------------------------------------------------------------------------------------
# Function to Verify Admin approval Mode - whether script is launched using Administrative credentials
# ----------------------------------------------------------------------------------------------------
Function Test-AdminApprovalMode() {
    return ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator");
}

# --------------------------------------------------------------------------------------------------
# This function will return whether current server provisioning method is CoRE build or CoRE modules
# --------------------------------------------------------------------------------------------------
Function Get-CoREInstallMode{
    #Looking for CoRE Native Content
    $buildconf = "$env:systemdrive\SUPPORT\buildconfig.xml"
    $appsXml = "$env:systemdrive\SUPPORT\CoREModules.xml"
    $installerLog = "$env:systemdrive\SUPPORT\CoREModulesInstaller.log"
    If ($psScriptRoot.ToUpper().contains("SUPPORT") -and (Test-Path -Path $buildconf )`
    -and (Test-Path -Path $appsXml) -and (Test-Path -Path $installerLog)){
        #Looking to see if the CoRE Load has been completed (helpful if people are running modules in same source directory as expected in CoRE)
        If (Get-Content $installerLog  | Select-String -Pattern "CoREModulesInstaller has finished executing"){
            Return "Modular" #Detected as running as a standalone modue
        }
        #Looking to see if the current working directory is the same as what is listed in the CoRE Apps installer XML
        [XML]$CoREAppsRead = Get-Content -Path $appsXml
        ForEach ($CoREApp in $CoREAppsRead.NewDataSet._dtApps){
            If ($CoREApp.appFolderPath -Contains $psScriptRoot){
               Return "Build" #Detected as running within the original Windows Server CoRE Install process 
            }
        }
        "Modular" #Detected as running as a standalone modue
    }
    Else {
        "Modular" #Detected as running as a standalone modue
     }
}

# ---------------------------------------------------------------------------------
# If module need to set branding information in Registry, this function can be used
# ---------------------------------------------------------------------------------
Function Set-CoREBrandingRegistry {    
    param(
        $RegPath = "HKLM:\SOFTWARE\DXC\CoRE", # default CoRE registry location
        $BrandingName, # name of branding element..like SNMP, IPv6, etc.
        $BrandingValue # value for branding element
    )

    # if CoRE registry location doesn't exist then create it
    if(-not (Test-Path $RegPath)) { New-Item $RegPath -Force | Out-Null }

    #Append Script InstallMode with Branding
    try {
        Set-ItemProperty -Path $RegPath -Name $BrandingName -Value $BrandingValue -ErrorAction Stop
    }
    catch {
        $_ # output error object
        Write-CodeModulesLog -Message "Error setting registry branding for $brandingname, see log for details"
        Write-CodeModulesLog -Message ($_ | Out-String)
    }
}

# ------------------------------------------------------------------------------------
# Identify whether the server installation Mode is ServerCore full or Minshell or Nano
# ------------------------------------------------------------------------------------
Function Get-OSInstallMode([Switch] $ShortName) {

	# get interface mode - method is different for w2k8r2 and w2k12+
    #https://msdn.microsoft.com/en-us/library/hh846315%28v=vs.85%29.aspx -> for w2k12 and above
    if((get-ciminstance -ClassName win32_operatingsystem).Version.startsWith("6.1.")) {
        # this is windows server 2008 R2
        #https://msdn.microsoft.com/en-us/library/aa394239(v=vs.85).aspx
        $OSSKU = (get-ciminstance -ClassName win32_operatingsystem).operatingsystemSKU
		if($OSSKU -in (7,8,10)) { # standard, datacenter, enterprise gui
            $Mode = "Server with a GUI (Full GUI)"    
        }
        elseif($OSSKU -in (12,13,14)) { # standard, datacenter, enterprise core
            $Mode = "Server Core"
        }
        else { $Mode = "Unidentified" }

        # if shortname is needed then return it
        if($ShortName.IsPresent) {
		    Switch($Mode) {
			    "Server with a GUI (Full GUI)" { $Mode = "Full"; }
			    "Server Core" { $Mode = "Core"; }
		    }
	    }
    }
    else { # it is windows servfer 2012 and above
	    $ServerLevels = Get-Item "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Server\ServerLevels"

	    if($ServerLevels.GetValue("NanoServer") -eq "1") { $Mode  = "Nano" }
	    elseif(($ServerLevels.GetValue("Server-Gui-Shell") -eq "1") -and ($ServerLevels.GetValue("Server-Gui-Mgmt") -eq "1")) { $Mode = "Server with a GUI (Full GUI)"; }
	    elseif($ServerLevels.GetValue("Server-Gui-Mgmt") -eq "1") { $Mode = "Minimal Server Interface"; }
	    elseif($ServerLevels.GetValue("ServerCore") -eq "1") { $Mode = "Server Core" }
	
	    if($ShortName.IsPresent) {
		    Switch($Mode) {
			    "Server with a GUI (Full GUI)" { $Mode = "Full"; }
			    "Server Core" { $Mode = "Core"; }
			    "Minimal Server Interface" { $Mode = "Minshell"; }
                # for nano, it will be "Nano" as above
		    }
	    }
    }
	
    return $Mode
}

# -------------------------------------------------------------------------------------
# this function will return XML nodes based on given xml variable and XPath query
# if query does not result in any nodes, a blank array is returned. you can check
# returnvar.count to see if anything was returned. 0 means query didn't return anything
# TODO: utilize return object (like in Ansible)
# --------------------------------------------------------------------------------------
Function Get-WCXMLNodes {
param(
    $Xml,
    $XPath
)
    # detect if running on nano. if yes then use different set of xml function call
    $osm = Get-OSInstallMode -ShortName # Nano, Full, Core and MinShell
    
    # check OS SKU and use xml calls accordingly
    if($osm -eq 'Nano') { # nano server
        try {
            $res = @([System.Xml.XmlDocumentXPathExtensions]::SelectNodes($Xml,$XPath))
            $res # return the result
        }
        catch { # error occured. user need to check if returned item is array or not
            # $_.Exception.Message # write to log file
            $null
        }
    }
    else { # its full or core
        try {
            $res = $Xml.SelectNodes($XPath)
            $res
        }
        catch { # error occured. user need to check if returned item is array or not
            #$_.Exception.Message
            $null
        }
    }
}

# This function will test if this script is running in the context of CoRE automated build or not
# ----------------------------------------------------------------------------------------------
Function Test-IsCoREAutomatedBuild {
    # if buildconfig.xml exist and check if it is running in auto-build mode
    If(Test-Path -Path "$env:systemdrive\SUPPORT\buildconfig.xml") {
        [xml]$ConfigFile = Get-Content "$env:systemdrive\SUPPORT\buildconfig.xml"
        $autoBuild = $ConfigFile.BuildManager.AutomatedBuild
    }
    else { # this is not running in auto-build (imfact, its likely CoRE modular)
        $autoBuild = "false"
    }
    $autoBuild # return whether it is auto build or not
}

# this function will write script header for all code modules - should be called at the begining of each module
# --------------------------------------------------------------------------------------------------------------
function Write-CodeModuleInfo($ModuleName) {
    $InstallMode = Get-CoREInstallMode
    $osCaption = (Get-WmiObject -Class win32_OperatingSystem).caption
    $osInstallMode = Get-OSInstallMode
    Write-CodeModulesLog -Message "Platform x86 CoRE - $ModuleName module"
    Write-CodeModulesLog -Message "Powershell Version: $($psversiontable.PSVersion.ToString())"
    Write-CodeModulesLog -Message "CoRE installation mode detected is $InstallMode"
    Write-CodeModulesLog -Message "$osCaption - running in $osInstallMode mode"
    Write-CodeModulesLog -Message "" # blank line (intentional)
}
