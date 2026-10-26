# Local code sync only. Never export DGN/MDB, private assets, credentials or runtime.
param([ValidateSet('Push','Pull')][string]$Action='Push')
$ErrorActionPreference='Stop'
[Console]::OutputEncoding=New-Object Text.UTF8Encoding($false)
Set-Location -LiteralPath $PSScriptRoot
$git=Get-Command git -CommandType Application -ErrorAction SilentlyContinue
if(-not $git){Write-Host 'Install Git for Windows first: winget install --id Git.Git -e --source winget';exit 1}
function Git([string[]]$Arguments) {
 $ErrorActionPreference='Continue'
 & $git.Source @Arguments
 if($LASTEXITCODE -ne 0){throw ('Git failed: '+($Arguments -join ' ')+'. Local files and commits are retained.')}
}
try {
 if(-not (Test-Path -LiteralPath (Join-Path $PSScriptRoot '.git'))){throw 'Use the SonMap-Dev workspace package for GitHub sync, not the installed App folder.'}
 $origin=(Git @('remote','get-url','origin')).Trim()
 if($origin -notin @('https://github.com/tohoaison1mthg-oss/SonMap-.git','https://github.com/tohoaison1mthg-oss/SonMap-')){throw 'Origin does not match the SonMap repository. No upload performed.'}
 $branch='codex/sonmap-topology-ui'
 $changes=@(Git @('ls-files','--modified','--deleted','--others','--exclude-standard'))+@(Git @('diff','--cached','--name-only'))
 $changes=@($changes | Where-Object {$_} | Sort-Object -Unique)
 foreach($file in $changes) {
  $leaf=[IO.Path]::GetFileName($file);$extension=[IO.Path]::GetExtension($file)
  if(($extension -eq '.json' -and $leaf -notin @('admin_catalog.json','MANIFEST.json')) -or ($leaf -notin @('VERSION','.gitignore','.gitattributes') -and $extension -notin @('.py','.ps1','.cmd','.bas','.cls','.cs','.md','.ico','.txt','.json','.code-workspace'))){throw ('Not an approved source file; sync stopped: '+$file)}
  if($file -match '(^|/)(data|assets|runtime|exports|SonMap_backups|\.venv[^/]*)(/|$)' -or $file -match '(^|/)(settings\.json|\.env[^/]*)$' -or $file -match '\.(mdb|dgn|mvba|dll|exe|zip|key|pem|pfx|lic)$'){throw ('Private/generated file detected; sync stopped: '+$file)}
 }
 Git @('fetch','origin','--tags')
 if($Action -eq 'Pull') {
  if($changes.Count){throw 'Save/upload your code changes with Gui_len_GitHub.cmd before pulling.'}
  Git @('merge','--ff-only',('origin/'+$branch))
  Write-Host 'Source updated. Run Lam_viec_laptop.cmd.';exit 0
 }
 if($changes.Count) {
  $current=[version]([IO.File]::ReadAllText((Join-Path $PSScriptRoot 'VERSION')).Trim())
  $head=[version]((Git @('show','HEAD:VERSION')).Trim())
  $remote=[version]((Git @('show',('origin/'+$branch+':VERSION'))).Trim())
  $latest=if($head -gt $remote){$head}else{$remote}
  foreach($tag in @(Git @('tag','--list','v*'))) {
   if($tag -match '^v(\d+\.\d+)$'){$tagVersion=[version]$Matches[1];if($tagVersion -gt $latest){$latest=$tagVersion}}
  }
  foreach($reference in @(Git @('for-each-ref','--format=%(refname)','refs/remotes/origin'))) {
   $ErrorActionPreference='Continue'
   $candidate=& $git.Source show ($reference+':VERSION') 2>$null
   $readCode=$LASTEXITCODE;$ErrorActionPreference='Stop'
   if($readCode -eq 0 -and $candidate -match '^\d+\.\d+$'){$candidateVersion=[version]$candidate;if($candidateVersion -gt $latest){$latest=$candidateVersion}}
  }
  if($current -le $latest){$current=[version]($latest.Major.ToString()+'.'+($latest.Minor+1).ToString())}
  $version=$current.Major.ToString()+'.'+$current.Minor.ToString()
  [IO.File]::WriteAllText((Join-Path $PSScriptRoot 'VERSION'),$version+"`n",(New-Object Text.UTF8Encoding($false)))
  $changelog=Join-Path $PSScriptRoot 'CHANGELOG.md'
  $entry="## V$version - laptop development snapshot`n`nLocal code changes; Windows/V8i validation is not implied.`n`n"
  [IO.File]::WriteAllText($changelog,$entry+[IO.File]::ReadAllText($changelog),(New-Object Text.UTF8Encoding($false)))
  $ErrorActionPreference='Continue';$name=& $git.Source config user.name;$ErrorActionPreference='Stop'
  if(-not $name){Git @('config','user.name','SonMap Laptop');Git @('config','user.email','sonmap-laptop@localhost')}
  Git @('add','--all')
  Git @('commit','-m',('Laptop development snapshot V'+$version))
 }
 $ErrorActionPreference='Continue'
 & $git.Source merge-base --is-ancestor ('origin/'+$branch) HEAD
 $ancestor=$LASTEXITCODE
 $ErrorActionPreference='Stop'
 if($ancestor -gt 1){throw 'Could not compare local/remote history.'}
 $sha=(Git @('rev-parse','--short','HEAD')).Trim()
 $destination=if($ancestor -eq 0){$branch}else{'laptop/snapshot-'+$sha}
 # Divergence is uploaded on a separate branch; no force push, rebase or data loss.
 Git @('push','origin',('HEAD:refs/heads/'+$destination))
 Write-Host ('Saved code: https://github.com/tohoaison1mthg-oss/SonMap-/tree/'+$destination)
 Write-Host 'Open that branch from your cloud session to continue. Windows Git may ask you to sign in through its credential manager.'
} catch {Write-Host $_.Exception.Message;exit 1}
