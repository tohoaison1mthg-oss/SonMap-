param([string]$Root=$PSScriptRoot,[string]$UsersDirectory)
$ErrorActionPreference='Stop'
try {
 if(-not $UsersDirectory){$UsersDirectory=Join-Path $env:ProgramData 'Bentley\MicroStation V8i (SELECTseries)\WorkSpace\Users'}
 $original=Join-Path $UsersDirectory 'VietMapXM.ucf'
 if(-not(Test-Path -LiteralPath $original)){throw 'Cannot find the existing VietMapXM user configuration.'}
 $source=[IO.File]::ReadAllText($original)
 $lines=$source -split "`r?`n"|Where-Object {$_ -notmatch '^\s*(MS_INIT\s*=|MS_VBAAUTOLOADPROJECTS\s*[=><]|_USTN_USERDESCR\s*=)'}
 $project=(Join-Path $Root 'ThanhTanApp.mvba').Replace('\','/')
 $text=($lines -join "`r`n")+"`r`n# SonMap independent V7 profile - original VietMapXM.ucf is unchanged`r`n_USTN_USERDESCR = SonMap V7`r`nMS_INIT =`r`nMS_OPENV7 = 3`r`nMS_VBAAUTOLOADPROJECTS = $project`r`n"
 $path=Join-Path $UsersDirectory 'SonMap.ucf'
 if(Test-Path -LiteralPath $path){Copy-Item -LiteralPath $path -Destination (Join-Path $Root ('data\SonMap-before-'+(Get-Date -Format 'yyyyMMddHHmmss')+'.ucf')) -Force}
 [IO.File]::WriteAllText($path,$text,[Text.Encoding]::ASCII)
 @{status='ready';profile=$path;original=$original;description='Independent SonMap V7 configuration. No VietMap plugin loaded.'}|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $Root 'data\fast-workspace.json') -Encoding UTF8
 Write-Output 'READY: SonMap V7 user profile created; original VietMapXM profile unchanged.'
}catch{Write-Output $_.Exception.Message;exit 1}
