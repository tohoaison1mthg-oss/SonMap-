VERSION 1.0 CLASS
BEGIN
  MultiUse = -1
END
Attribute VB_Name = "LH_DgnMonitor"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = False
Attribute VB_Exposed = False
Option Explicit
Private WithEvents hooks As MicroStationDGN.Application
Private Sub Class_Initialize()
    Set hooks = MicroStationDGN.Application
End Sub
Private Sub Class_Terminate()
    Set hooks = Nothing
End Sub
Private Sub hooks_OnDesignFileOpened(ByVal DesignFileName As String)
    LH_KhoiDong.MoBangThuocTinh DesignFileName
End Sub
