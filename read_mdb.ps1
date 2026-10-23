param([string]$MdbPath,[string]$JsonPath)
$ErrorActionPreference='Stop'
$connection=New-Object System.Data.OleDb.OleDbConnection
$connection.ConnectionString='Provider=Microsoft.Jet.OLEDB.4.0;Data Source='+$MdbPath+';Mode=Read;'
try {
 $connection.Open()
 $command=$connection.CreateCommand()
 $command.CommandText='SELECT ID,ToBD,TCT,DienTich,TenChu,DiaChi,DiaChiThuaDatChiTiet,Xudong,LRD,MaLD,Geometry FROM ThuaDat ORDER BY ToBD,TCT,ID'
 $reader=$command.ExecuteReader()
 $rows=New-Object System.Collections.Generic.List[object]
 while($reader.Read()) {
  $item=@{}
  for($column=0;$column -lt $reader.FieldCount;$column++) {
   $value=$reader[$column]
   if($value -is [DBNull]){$value=$null}
   if($value -is [byte[]]){$value=[Convert]::ToBase64String($value)}
   $item[$reader.GetName($column)]=$value
  }
  $rows.Add($item)
 }
 $json=ConvertTo-Json -InputObject @($rows.ToArray()) -Depth 5
 [IO.File]::WriteAllText($JsonPath,$json,(New-Object Text.UTF8Encoding($false)))
} finally {$connection.Dispose()}
