@echo off
START delete_queues_helper.bat
SLEEP 6
for /F "tokens=1" %%i in (queues.txt) do call :process %%i
rm queues.txt
:process
set VAR1=%1
set replaced=%VAR1:game_=%
IF NOT "%VAR1%"=="" (
  If NOT "%VAR1%"=="%replaced%" (
    echo deleting queue %VAR1%
    rabbitmqctl.bat delete_queue %VAR1%
  )
)
goto :EOF