# Read-only configuration diagnostics. Never modifies VietMapXM, licensing, or DGN.
param([string]$VietMapRoot='C:\VietMapXM',[string]$OutputPath)
$ErrorActionPreference='Stop'
if(-not $OutputPath){$OutputPath=Join-Path $PSScriptRoot 'data\vietmapxm-diagnostic.json'}
$report=[ordered]@{schema=1;sonmap_version=([IO.File]::ReadAllText((Join-Path $PSScriptRoot 'VERSION'))).Trim();process_bits=([IntPtr]::Size*8);vietmap_root=$VietMapRoot;root_exists=(Test-Path -LiteralPath $VietMapRoot);configuration=@();warnings=@();microstation=@{connected=$false}}
$locations=@($VietMapRoot,(Join-Path $env:ProgramData 'Bentley\MicroStation V8i (SELECTseries)\WorkSpace\Users'))
$seen=@{}
foreach($location in $locations) {
 if(-not (Test-Path -LiteralPath $location)){continue}
 $errors=@()
 $files=@(Get-ChildItem -LiteralPath $location -File -Recurse -ErrorAction SilentlyContinue -ErrorVariable +errors | Where-Object {$_.Extension -in @('.cfg','.ucf','.pcf')} | Sort-Object FullName)
 if($errors.Count){$report.warnings+=('Some configuration paths could not be read under '+$location)}
 if($files.Count -gt 500){$report.warnings+='Configuration listing limited to 500 files.';$files=@($files | Select-Object -First 500)}
 foreach($file in $files) {
  if($seen.ContainsKey($file.FullName)){continue};$seen[$file.FullName]=$true
  try {
   $text=[IO.File]::ReadAllText($file.FullName)
   $selected=@()
   foreach($line in ($text -split "`r?`n")) {
    # Explicit allowlist of CAD resource settings only, not arbitrary environment/credential values.
    if($line -match '^\s*(MS_OPENV7|MS_INIT|MS_DGNAPPS|MS_MDLAPPS|MS_VBAAUTOLOADPROJECTS|MS_VBASEARCHDIRECTORIES|MS_SEEDFILES|MS_CELL|MS_SYMBRSRC|MS_FONTPATH|MS_RSC|_USTN_WORKSPACEROOT|_USTN_USER|_USTN_PROJECT)\s*[=<>]'){$selected+=$line.Trim()}
   }
   if($selected.Count){$report.configuration+=@{path=$file.FullName;settings=$selected}}
  } catch {$report.warnings+=('Cannot read configuration: '+$file.FullName)}
 }
}
try {
 $app=[Runtime.InteropServices.Marshal]::GetActiveObject('MicroStationDGN.Application')
 $report.microstation=@{connected=$true;active_file=[string]$app.ActiveDesignFile.FullName;active_model=[string]$app.ActiveModelReference.Name}
 try {$report.microstation.default_model=[string]$app.ActiveDesignFile.DefaultModelReference.Name}catch{$report.microstation.default_model_error=$_.Exception.Message}
 try {$report.microstation.model_count=[int]$app.ActiveDesignFile.Models.Count}catch{$report.microstation.model_count_error=$_.Exception.Message}
 try {$report.microstation.is_3d=[bool]$app.ActiveModelReference.Is3D}catch{}
 try {$report.microstation.master_unit=[string]$app.ActiveModelReference.MasterUnit.Label}catch{}
} catch {$report.microstation.error=$_.Exception.Message}
$parent=Split-Path -Parent ([IO.Path]::GetFullPath($OutputPath));[void](New-Item -ItemType Directory -Path $parent -Force)
[IO.File]::WriteAllText($OutputPath,(ConvertTo-Json -InputObject $report -Depth 10),(New-Object Text.UTF8Encoding($false)))
Write-Host ('Saved read-only diagnostic: '+$OutputPath)
if($report.microstation.connected){Write-Host 'V8i COM connection: OK'}else{Write-Host 'V8i COM connection: unavailable; open V8i and the DGN, then run this tool again.'}
Write-Host 'No DGN, MDB, configuration, DLL or licensing file was modified.'
