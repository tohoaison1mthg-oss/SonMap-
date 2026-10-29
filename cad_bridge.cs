using System;
using System.IO;
using System.Collections.Generic;
using System.Web.Script.Serialization;
using System.Windows.Forms;
using B = Bentley.Interop.MicroStationDGN;
using System.Runtime.InteropServices;

internal sealed class SonMapCadBridge : Bentley.MicroStation.AddIn {
    [DllImport("user32.dll")] private static extern bool SetForegroundWindow(IntPtr window);
    [DllImport("user32.dll")] private static extern bool IsIconic(IntPtr window);
    [DllImport("user32.dll")] private static extern bool ShowWindow(IntPtr window,int command);
    private Timer timer;
    private string directory;
    private JavaScriptSerializer json;
    private SonMapCadBridge(IntPtr descriptor) : base(descriptor) {}
    protected override int Run(string[] args) {
        directory = Path.GetDirectoryName(GetType().Assembly.Location);
        json = new JavaScriptSerializer();
        json.MaxJsonLength = int.MaxValue;
        timer = new Timer(); timer.Interval = 40;
        timer.Tick += Tick; timer.Start();
        var process=System.Diagnostics.Process.GetCurrentProcess();
        File.WriteAllText(Path.Combine(directory,"ready.json"),json.Serialize(new {pid=process.Id,start=process.StartTime.ToUniversalTime().Ticks}));
        return 0;
    }
    private void Tick(object sender, EventArgs ignored) {
        try {SonMapInProcessRecords.CheckFocusContext(Bentley.MicroStation.InteropServices.Utilities.ComApp);} catch {}
        string requestPath=Path.Combine(directory,"request.json");
        if(!File.Exists(requestPath))return;
        timer.Stop();
        Dictionary<string,object> request=null;
        try {
            request=(Dictionary<string,object>)json.DeserializeObject(File.ReadAllText(requestPath));
            File.Delete(requestPath);
            var app=Bentley.MicroStation.InteropServices.Utilities.ComApp;
            string source=Convert.ToString(request["source"]);
            if(!String.Equals(Path.GetFullPath(app.ActiveDesignFile.FullName),Path.GetFullPath(source),StringComparison.OrdinalIgnoreCase))
                throw new InvalidOperationException("Active DGN changed; operation cancelled.");
            var model=app.ActiveModelReference;
            if(model.Is3D)throw new InvalidOperationException("Only 2D cadastral models are supported.");
            string wantedModel=Convert.ToString(request["model"]);
            if(wantedModel.Length>0 && model.Name!=wantedModel)throw new InvalidOperationException("Active model changed; operation cancelled.");
            string action=Convert.ToString(request["action"]);
            object result;
            if(action=="extract") {
                int[] levels=Integers(request["levels"]);
                int[] text=request["text_levels"]==null?null:Integers(request["text_levels"]);
                bool defaultModel=app.ActiveDesignFile.Models.Count==1 || Object.ReferenceEquals(model,app.ActiveDesignFile.DefaultModelReference) || model.Name==app.ActiveDesignFile.DefaultModelReference.Name;
                result=SonMapInProcessRecords.ExtractJson(app,model,levels,Convert.ToBoolean(request["arcs"]),Convert.ToBoolean(request["keep_complex"]),Convert.ToDouble(request["tolerance"]),defaultModel,text);
            } else if(action=="focus") {
                IntPtr window=System.Diagnostics.Process.GetCurrentProcess().MainWindowHandle;
                if(IsIconic(window))ShowWindow(window,9);
                SetForegroundWindow(window);
                SonMapInProcessRecords.Focus(app,Convert.ToDouble(request["x"]),Convert.ToDouble(request["y"]),Convert.ToDouble(request["span"]));
                result="FOCUSED";
            } else if(action=="clean") {
                result=SonMapClean.Run(app,(Dictionary<string,object>)request["project"]);
            } else if(action=="hide" || action=="restore") {
                result=SonMapView.Run(app,request,action=="restore");
            } else if(action=="save") {
                app.ActiveDesignFile.Save();result="ACTIVE_SOURCE_SAVED";
            } else throw new InvalidOperationException("Unsupported bridge action.");
            Reply(request,true,result);
        } catch(Exception error) {Reply(request,false,"Stage: "+SonMapClean.Stage+"\n"+error.ToString(),error is SonMapClean.RestoreFailed);}
        finally {timer.Start();}
    }
    private int[] Integers(object value) {
        var rows=(object[])value;var result=new int[rows.Length];
        for(int i=0;i<rows.Length;i++)result[i]=Convert.ToInt32(rows[i]);
        return result;
    }
    private void Reply(Dictionary<string,object> request,bool ok,object result,bool rescue=false) {
        string temporary=Path.Combine(directory,"response.tmp");
        File.WriteAllText(temporary,json.Serialize(new {id=request==null?null:request["id"],ok=ok,result=result,rescue_required=rescue}));
        string destination=Path.Combine(directory,"response.json");
        if(File.Exists(destination))File.Delete(destination);
        File.Move(temporary,destination);
    }
}
