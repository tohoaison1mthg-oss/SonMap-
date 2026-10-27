# Parameterized, transactional owner update. Python verifies and backs up the full MDB first.
param([Parameter(Mandatory=$true)][string]$MdbPath,[Parameter(Mandatory=$true)][string]$PlanPath)
$ErrorActionPreference='Stop'
$plan=Get-Content -LiteralPath $PlanPath -Raw -Encoding UTF8 | ConvertFrom-Json
if((Get-FileHash -LiteralPath $MdbPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $plan.sha256){throw 'MDB changed before update. Reopen parcel information.'}
$builder=New-Object Data.OleDb.OleDbConnectionStringBuilder
$builder.Provider='Microsoft.Jet.OLEDB.4.0';$builder['Data Source']=$MdbPath
$connection=New-Object Data.OleDb.OleDbConnection($builder.ConnectionString)
$transaction=$null
try {
 $connection.Open();$transaction=$connection.BeginTransaction()
 $command=$connection.CreateCommand();$command.Transaction=$transaction
 $command.CommandText='UPDATE ThuaDat SET TenChu=?, DiaChi=? WHERE ID=?'
 foreach($name in @('TenChu','DiaChi')) {
  $parameter=$command.Parameters.Add('@'+$name,[Data.OleDb.OleDbType]::VarWChar,255)
  $parameter.Value=[string]$plan.$name
 }
 $parameter=$command.Parameters.Add('@ID',[Data.OleDb.OleDbType]::Integer);$parameter.Value=[int]$plan.ID
 if($command.ExecuteNonQuery() -ne 1){throw 'Owner update must affect exactly one parcel.'}
 $command.Dispose()
 $command=$connection.CreateCommand();$command.Transaction=$transaction
 $command.CommandText='SELECT TenChu,DiaChi FROM ThuaDat WHERE ID=?'
 $parameter=$command.Parameters.Add('@ID',[Data.OleDb.OleDbType]::Integer);$parameter.Value=[int]$plan.ID
 $reader=$command.ExecuteReader()
 if(-not $reader.Read() -or [string]$reader['TenChu'] -cne [string]$plan.TenChu -or [string]$reader['DiaChi'] -cne [string]$plan.DiaChi){throw 'Owner readback mismatch.'}
 $reader.Close();$command.Dispose()
 $transaction.Commit();$transaction=$null
 Write-Output 'OWNER_UPDATED_VERIFIED'
} catch {if($transaction){$transaction.Rollback()};throw}
finally {$connection.Dispose()}
