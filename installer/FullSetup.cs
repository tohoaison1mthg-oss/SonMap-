using System;
using System.IO;
using System.IO.Compression;
using System.Diagnostics;
using System.Reflection;
using System.Security.Cryptography;
using System.Windows.Forms;
class FullSetup {
 static string ExpectedHash="BUNDLE_HASH";
 static string Version="APP_VERSION";
 static string Bundle(string stage) {
  string path=Path.Combine(stage,"bundle.zip");
  using(var input=Assembly.GetExecutingAssembly().GetManifestResourceStream("bundle.zip"))
  using(var output=File.Create(path))input.CopyTo(output);
  using(var sha=SHA256.Create())using(var input=File.OpenRead(path)) {
   string hash=BitConverter.ToString(sha.ComputeHash(input)).Replace("-","").ToLowerInvariant();
   if(hash!=ExpectedHash)throw new Exception("Installer checksum mismatch.");
  }
  return path;
 }
 [STAThread] static int Main(string[] args) {
  string stage=Path.Combine(Path.GetTempPath(),"SonMapFull-"+Guid.NewGuid().ToString("N"));
  Directory.CreateDirectory(stage);
  try {
   if(!Environment.Is64BitOperatingSystem)throw new Exception("SonMap requires Windows 64-bit with MicroStation V8i.");
   string bundle=Bundle(stage);
   using(var zip=ZipFile.OpenRead(bundle)) {
    foreach(string name in new[]{"Cai_dat.ps1","payload.zip","resources.zip","prerequisites/python-3.12.10-amd64.exe"})
     if(zip.GetEntry(name)==null)throw new Exception("Incomplete installer: "+name);
    if(args.Length==1 && args[0]=="--verify"){Console.WriteLine("PASS: SonMap+ V"+Version+" bundle SHA256 and required entries");zip.Dispose();Directory.Delete(stage,true);return 0;}
    foreach(var entry in zip.Entries) {
     string target=Path.GetFullPath(Path.Combine(stage,entry.FullName));
     if(!target.StartsWith(stage+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase))throw new Exception("Invalid package path");
     if(entry.FullName.EndsWith("/"))continue;
     Directory.CreateDirectory(Path.GetDirectoryName(target));entry.ExtractToFile(target,false);
    }
   }
   if(args.Length==2 && args[0]=="--extract") {
    string destination=Path.GetFullPath(args[1]);
    if(Directory.Exists(destination)||File.Exists(destination))throw new Exception("Extraction destination already exists.");
    Directory.Move(stage,destination);Console.WriteLine(destination);return 0;
   }
   if(args.Length!=0)throw new Exception("Unknown setup arguments.");
   var form=new Form{Text="SonMap+ V"+Version+" - Cai dat",Width=570,Height=160,StartPosition=FormStartPosition.CenterScreen,ControlBox=false};
   form.Controls.Add(new Label{Text="Dang cai SonMap+, Python va thu vien offline.\r\nVui long doi; khong can cai rieng tung thanh phan.",Dock=DockStyle.Fill,Padding=new Padding(20)});
   form.Show();Application.DoEvents();
   string shell=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Windows),"System32/WindowsPowerShell/v1.0/powershell.exe");
   var info=new ProcessStartInfo(shell,"-NoProfile -ExecutionPolicy Bypass -File \""+Path.Combine(stage,"Cai_dat.ps1")+"\" -NoLaunch");
   info.UseShellExecute=false;info.CreateNoWindow=true;info.RedirectStandardOutput=true;info.RedirectStandardError=true;
   int code;string log;
   using(var p=Process.Start(info)) {
    var stdout=p.StandardOutput.ReadToEndAsync();var stderr=p.StandardError.ReadToEndAsync();
    while(!p.WaitForExit(100))Application.DoEvents();
    code=p.ExitCode;log=stdout.Result+Environment.NewLine+stderr.Result;
   }
   File.WriteAllText(Path.Combine(stage,"setup-result.log"),log);form.Close();
   if(code!=0){MessageBox.Show("Cai dat chua hoan tat.\r\nNhat ky: "+Path.Combine(stage,"setup-result.log")+"\r\n"+log,"SonMap+",MessageBoxButtons.OK,MessageBoxIcon.Warning);return code;}
   MessageBox.Show("Da cai SonMap+ V"+Version+".\r\n1. Mo MicroStation V8i va DGN cua ban.\r\n2. Mo SonMap+ tren Desktop.\r\nVBA duoc cap nhat tu dong khi xuat. Khong can VietMapXM.","SonMap+",MessageBoxButtons.OK,MessageBoxIcon.Information);
   Directory.Delete(stage,true);return 0;
  }catch(Exception e){Console.Error.WriteLine(e);if(args.Length==0)MessageBox.Show(e.Message+"\r\n"+stage,"SonMap+ - Loi cai dat");return 1;}
 }
}
