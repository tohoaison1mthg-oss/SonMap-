param([string]$Root=$PSScriptRoot)
$ErrorActionPreference='Stop'
# Per-user workspace: no writes to Bentley's installation or VietMapXM profiles.
$base=Join-Path $Root 'workspace'
$users=Join-Path $base 'Users'
$projects=Join-Path $base 'Projects'
foreach($path in @($users,$projects)){[void](New-Item -ItemType Directory -Path $path -Force)}
$forward=$Root.Replace('\','/')+'/'
$ucf=@'
# Generated SonMap workspace
_USTN_USERDESCR = SonMap+ Workspace
_USTN_PROJECTNAME = SonMap
_USTN_USERINTNAME = default
MS_OPENV7 = 3
MS_VBASEARCHDIRECTORIES > APP_DIRECTORY
MS_SYMBRSRC > $(_USTN_SYSTEMROOT)symb/*.rsc
MS_CELL > C:/VietMapXM/Bentley/WorkSpace/System/Cell/
MS_CELLLIST > C:/VietMapXM/Bentley/WorkSpace/System/Cell/*.cel
MS_SYMBRSRC > C:/VietMapXM/Bentley/WorkSpace/System/Symb/*.rsc
'@
$pcf=@'
# Generated SonMap project
_USTN_PROJECTDESCR = SonMap+ Project
MS_OPENV7 = 3
'@
[IO.File]::WriteAllText((Join-Path $users 'SonMap.ucf'),$ucf.Replace('APP_DIRECTORY',$forward),[Text.Encoding]::ASCII)
[IO.File]::WriteAllText((Join-Path $projects 'SonMap.pcf'),$pcf,[Text.Encoding]::ASCII)
@('-wuSonMap','-wpSonMap',('-ws_USTN_USER='+$users.Replace('\','/')+'/'),('-ws_USTN_PROJECT='+$projects.Replace('\','/')+'/'))
