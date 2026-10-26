# Resolve model identity independently of its display name, for V7/program-only files.
function ResolveSonMapModel($Design,[string]$Name,[bool]$DefaultRole=$false) {
 $default=$null
 try {$default=$Design.DefaultModelReference} catch {}
 if($DefaultRole) {
  if($null -ne $default){return $default}
  throw 'The source uses the default model, but the snapshot has no accessible default model.'
 }
 $names=New-Object 'System.Collections.Generic.List[string]'
 # Opening DefaultModelReference also initializes some program-only/V7 model collections.
 foreach($candidate in $Design.Models) {
  $candidateName=[string]$candidate.Name
  $names.Add($candidateName)
  if($candidateName -eq $Name){return $candidate}
 }
 if($null -ne $default -and [string]$default.Name -eq $Name){return $default}
 # Do not silently choose another model in a multi-model drawing.
 throw ('Model not found: '+$Name+'. Available models: '+($names -join ', '))
}

function TestSonMapDefaultModel($Design,$ActiveModel) {
 # A single-model source provides positive evidence even if V7 aliases its name.
 try {if([int]$Design.Models.Count -eq 1){return $true}} catch {}
 try {if($ActiveModel.IsDefault -eq $true){return $true}} catch {}
 try {
  $default=$Design.DefaultModelReference
  if($null -ne $default -and [string]$ActiveModel.Name -eq [string]$default.Name){return $true}
 } catch {}
 return $false
}
