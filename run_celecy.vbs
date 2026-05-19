Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "D:\soft\phone_record_syn"  ' 修改为你的项目路径
WshShell.Run "cmd /c celery -A phone_record_syn worker --pool=threads --concurrency=12 --loglevel=info >> celery.log 2>&1", 0, False
WshShell.Run "cmd /c celery -A phone_record_syn beat --loglevel=info >> beat.log 2>&1", 0, False