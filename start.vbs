Set ws = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
ws.CurrentDirectory = scriptDir

' --- Detect Python / Pythonw -------------------------------------------------
pythonExe = ""
pythonwExe = ""

If ws.Run("py -3.8 -c ""import sys""", 0, True) = 0 Then
    pythonExe = "py -3.8"
End If

If pythonExe = "" And ws.Run("python -c ""import sys""", 0, True) = 0 Then
    pythonExe = "python"
End If

If pythonExe = "" Then
    MsgBox "[DIP查询助手] 未找到可用的 Python，请先安装 Python 3.8+。", vbExclamation, "DIP"
    WScript.Quit 1
End If

quotedProbe = Chr(34) & "import sys, pathlib; print(pathlib.Path(sys.executable).with_name('pythonw.exe'))" & Chr(34)
Set exec = ws.Exec(pythonExe & " -c " & quotedProbe)
pythonwProbe = ""
Do While exec.Status = 0
    WScript.Sleep 50
Loop
If Not exec.StdOut.AtEndOfStream Then
    pythonwProbe = Trim(exec.StdOut.ReadAll())
End If
If pythonwProbe <> "" And fso.FileExists(pythonwProbe) Then
    pythonwExe = Chr(34) & pythonwProbe & Chr(34)
Else
    pythonwExe = pythonExe
End If

' --- Check dependencies ------------------------------------------------------
If ws.Run(pythonExe & " -c ""import pandas, openpyxl, PySide2""", 0, True) <> 0 Then
    MsgBox "[DIP查询助手] 缺少依赖，请先执行: pip install -r requirements.txt", vbExclamation, "DIP"
    WScript.Quit 1
End If

' --- Build database (with PYTHONPATH so scripts can find the package) --------
Set env = ws.Environment("Process")
env("PYTHONPATH") = scriptDir & "\src"

quotedBuildScript = Chr(34) & scriptDir & "\scripts\build_data.py" & Chr(34)
rc = ws.Run(pythonExe & " " & quotedBuildScript, 0, True)
If rc <> 0 Then
    MsgBox "[DIP查询助手] 查询库重建失败，请检查数据源目录。", vbExclamation, "DIP"
    WScript.Quit 1
End If

' --- Launch GUI with pythonw (zero console window) --------------------------
quotedRunApp = Chr(34) & scriptDir & "\run_app.py" & Chr(34)
ws.Run pythonwExe & " " & quotedRunApp, 0, False
