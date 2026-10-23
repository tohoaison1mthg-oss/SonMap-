using System;
using System.IO;
using System.IO.Compression;
using System.Reflection;
using System.Diagnostics;
using System.Windows.Forms;
class Setup {
 [STAThread] static int Main(string[] args) {
  try {
   if(args.Length>0 && args[0]=="--verify") {
    using(var s=Assembly.GetExecutingAssembly().GetManifestResourceStream("payload.zip"))
    using(var zip=new ZipArchive(s,ZipArchiveMode.Read)) {
     if(zip.GetEntry("app.py")==null || zip.GetEntry("runtime/python.exe")==null || zip.GetEntry("workflow.py")==null)throw new Exception("Incomplete package");
     Console.WriteLine("PASS: embedded payload; entries="+zip.Entries.Count);
    }return 0;
   }
   string stage=Path.Combine(Path.GetTempPath(),"ThanhTanOneClick-"+Guid.NewGuid().ToString("N"));Directory.CreateDirectory(stage);
   foreach(string name in new[]{"payload.zip","install.ps1"})using(var input=Assembly.GetExecutingAssembly().GetManifestResourceStream(name))using(var output=File.Create(Path.Combine(stage,name)))input.CopyTo(output);
   bool test=args.Length==2 && args[0]=="--test";
   var form=new Form{Text="SonMap+ V10.3 — cài đặt",Width=560,Height=160,StartPosition=FormStartPosition.CenterScreen,ControlBox=false};
   form.Controls.Add(new Label{Text="Đang sao lưu và cập nhật ThanhTanApp…\r\nVui lòng đợi, không cần sao chép hay giải nén file.",Dock=DockStyle.Fill,Padding=new Padding(20)});
   if(!test)form.Show();Application.DoEvents();
   var psi=new ProcessStartInfo(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Windows),"SysWOW64\\WindowsPowerShell\\v1.0\\powershell.exe"));
   psi.Arguments="-NoProfile -ExecutionPolicy Bypass -File \""+Path.Combine(stage,"install.ps1")+"\""+(test?" -TestRoot \""+Path.GetFullPath(args[1])+"\"":"");
   psi.UseShellExecute=false;psi.CreateNoWindow=true;psi.RedirectStandardOutput=true;psi.RedirectStandardError=true;
   var p=Process.Start(psi);var stdout=p.StandardOutput.ReadToEndAsync();var stderr=p.StandardError.ReadToEndAsync();
   while(!p.WaitForExit(100)){Application.DoEvents();}
   string log=stdout.Result+Environment.NewLine+stderr.Result;
   File.WriteAllText(Path.Combine(stage,"result.log"),log);form.Close();
   if(test){Console.WriteLine(log);return p.ExitCode;}
   MessageBox.Show(p.ExitCode==0?"Đã cài và mở SonMap+ V10.3.\r\nMở MicroStation V8i và DGN nguồn có MDB cùng tên.\r\nVBA sẽ được cập nhật tự động khi xuất nếu chưa kết nối lúc cài.":"Chưa hoàn tất cài đặt.\r\n"+log+"\r\nNhật ký: "+Path.Combine(stage,"result.log"),"SonMap+ V10.3",MessageBoxButtons.OK,p.ExitCode==0?MessageBoxIcon.Information:MessageBoxIcon.Warning);
   return p.ExitCode;
  }catch(Exception e){Console.Error.WriteLine(e);MessageBox.Show(e.Message,"ThanhTanApp — lỗi cài đặt");return 1;}
 }
}
