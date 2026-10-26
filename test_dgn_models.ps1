# Run with Windows PowerShell; pure fake objects, no MicroStation or disk changes.
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'dgn_models.ps1')
$primary=[pscustomobject]@{Name='';IsDefault=$true}
$secondary=[pscustomobject]@{Name='Other';IsDefault=$false}
$design=[pscustomobject]@{DefaultModelReference=$primary;Models=@($primary,$secondary)}
if((ResolveSonMapModel $design 'Default' $true) -ne $primary){throw 'Default alias resolution failed.'}
if((ResolveSonMapModel $design 'Other' $false) -ne $secondary){throw 'Named model resolution failed.'}
$failed=$false
try{ResolveSonMapModel $design 'Default' $false}catch{$failed=$true}
if(-not $failed){throw 'Unexpected fallback in multi-model file.'}
$single=[pscustomobject]@{DefaultModelReference=$primary;Models=@($primary)}
$active=[pscustomobject]@{Name='Default';IsDefault=$false}
if(-not (TestSonMapDefaultModel $single $active)){throw 'Single-model alias identification failed.'}
if(TestSonMapDefaultModel $design $secondary){throw 'Named model must not be treated as default.'}
$programFile=[pscustomobject]@{DefaultModelReference=$primary;Models=@()}
if((ResolveSonMapModel $programFile 'Default' $true) -ne $primary){throw 'Program-only default reference failed.'}
Write-Output 'PASS: default alias, named model, no ambiguous fallback, single model and program-only collection.'
