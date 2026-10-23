Attribute VB_Name = "LH_KhoiDong"
Option Explicit
Private monitor As LH_DgnMonitor
Public Sub OnProjectLoad()
    If monitor Is Nothing Then Set monitor = New LH_DgnMonitor
End Sub
Public Sub OnProjectUnload()
    Set monitor = Nothing
End Sub
Public Sub MoAppThanhTan()
    OnProjectLoad
    Dim currentPath As String
    ' Manual launch may also be invoked before a DGN is active.
    On Error Resume Next
    currentPath = ActiveDesignFile.FullName
    On Error GoTo 0
    If Len(currentPath) > 0 Then MoBangThuocTinh currentPath
End Sub
Public Sub MoBangThuocTinh(ByVal dgnPath As String)
    On Error GoTo Failed
    Dim fs As Object, stream As Object, python As String, command As String
    If Len(Trim$(dgnPath)) = 0 Then Exit Sub
    Set fs = CreateObject("Scripting.FileSystemObject")
    If Not fs.FileExists(fs.GetParentFolderName(dgnPath) & "\" & fs.GetBaseName(dgnPath) & ".mdb") Then Exit Sub
    Set stream = fs.CreateTextFile("C:\Users\tohoa\Documents\Codex\2026-10-12\referenced-chatgpt-conversation-this-is-an\outputs\ThanhTanApp\data\active_dgn.txt", True, True)
    stream.Write dgnPath: stream.Close
    python = "C:\Users\tohoa\Documents\EZDGN\.venv\Scripts\pythonw.exe"
    command = Chr$(34) & python & Chr$(34) & " " & Chr$(34) & "C:\Users\tohoa\Documents\Codex\2026-10-12\referenced-chatgpt-conversation-this-is-an\outputs\ThanhTanApp\app.py" & Chr$(34)
    CreateObject("WScript.Shell").Run command, 1, False
    Exit Sub
Failed:
    MsgBox "Cannot open ThanhTan app: " & Err.Description, vbExclamation
End Sub
