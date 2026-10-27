param([string]$MdbPath,[string]$JsonPath,[string]$SchemaPath)
$ErrorActionPreference='Stop'
$connection=New-Object System.Data.OleDb.OleDbConnection
$connection.ConnectionString='Provider=Microsoft.Jet.OLEDB.4.0;Data Source='+$MdbPath+';Mode=Read;'
try {
 $connection.Open()
 $command=$connection.CreateCommand()
 $command.CommandText='SELECT * FROM ThuaDat ORDER BY ToBD,TCT,ID'
 $reader=$command.ExecuteReader()
 if($SchemaPath) {
  $columns=@($reader.GetSchemaTable().Rows | ForEach-Object { @{name=[string]$_.ColumnName;type=[string]$_.DataType.FullName;size=[int]$_.ColumnSize;nullable=[bool]$_.AllowDBNull} })
  [IO.File]::WriteAllText($SchemaPath,(ConvertTo-Json -InputObject $columns -Depth 5),(New-Object Text.UTF8Encoding($false)))
 }
 $rows=New-Object System.Collections.Generic.List[object]
 while($reader.Read()) {
  $item=@{}
  for($column=0;$column -lt $reader.FieldCount;$column++) {
   $value=$reader[$column]
   if($value -is [DBNull]){$value=$null}
   if($value -is [byte[]]){$value=[Convert]::ToBase64String($value)}
   if($value -is [datetime]){$value=$value.ToString('o')}
   $item[$reader.GetName($column)]=$value
  }
  $rows.Add($item)
 }
 $json=ConvertTo-Json -InputObject @($rows.ToArray()) -Depth 5
 [IO.File]::WriteAllText($JsonPath,$json,(New-Object Text.UTF8Encoding($false)))
} finally {$connection.Dispose()}
