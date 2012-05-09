set pyfile=%~dp0\minecraftp
set pyinst=C:\Python27\pyinstaller-1.5-rc1
python "%pyinst%\Configure.py"
python "%pyinst%\Makespec.py" --onefile --noconsole --icon=minecraftp.ico "%pyfile%.py"
python "%pyinst%\Build.py" %pyfile%.spec
pause