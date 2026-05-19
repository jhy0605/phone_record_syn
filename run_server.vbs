Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "D:\soft\phone_record_syn"  ' 修改为你的项目路径
WshShell.Run "cmd /c python manage.py runserver 10.10.100.83:9000 >> servers.log 2>&1", 0, False