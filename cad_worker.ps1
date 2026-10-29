# One private 32-bit process per SonMap session. Scripts keep their own scope;
# compiled interop types are reused, but DGN/model checks run on every request.
$ErrorActionPreference='Stop'
[Console]::InputEncoding=New-Object Text.UTF8Encoding($false)
[Console]::OutputEncoding=New-Object Text.UTF8Encoding($false)
while($null -ne ($line=[Console]::ReadLine())) {
 $request=$null
 try {
  $request=$line | ConvertFrom-Json
  $name=[string]$request.script
  if([IO.Path]::GetFileName($name) -ne $name -or -not $name.EndsWith('.ps1')){throw 'Invalid script name.'}
  $path=Join-Path $PSScriptRoot $name
  if(-not (Test-Path -LiteralPath $path -PathType Leaf)){throw 'Missing script.'}
  $parameters=@{}
  $arguments=[string[]]@($request.arguments)
  $command=Get-Command -Name $path
  for($i=0;$i -lt $arguments.Count;$i++) {
   $key=$arguments[$i]
   if(-not $key.StartsWith('-')){throw 'Expected a named script parameter.'}
   $key=$key.Substring(1)
   if(-not $command.Parameters.ContainsKey($key)){throw ('Unknown script parameter: '+$key)}
   if($command.Parameters[$key].ParameterType -eq [Management.Automation.SwitchParameter]){$parameters[$key]=$true}
   else {
    $i++
    if($i -ge $arguments.Count){throw ('Missing parameter value: '+$key)}
    $parameters[$key]=$arguments[$i]
   }
  }
  $global:LASTEXITCODE=0
  $output=@(& $path @parameters 2>&1 | ForEach-Object {[string]$_})
  $response=@{id=$request.id;ok=($LASTEXITCODE -eq 0);output=($output -join "`n")}
 } catch {
  $response=@{id=$request.id;ok=$false;output=($_ | Out-String)}
 }
 [Console]::Out.WriteLine("`nSONMAP_RESPONSE "+(ConvertTo-Json -InputObject $response -Compress -Depth 5))
 [Console]::Out.Flush()
}
