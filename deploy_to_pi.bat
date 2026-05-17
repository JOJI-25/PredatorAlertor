@echo off
echo ========================================================
echo PredatorAlert Deployment Helper
echo ========================================================
echo This script will copy the current project to your Raspberry Pi.
echo.

:ASK_IP
set PI_IP=192.168.31.77
rem if "%PI_IP%"=="" goto ASK_IP

:ASK_USER
set PI_USER=predator_alert_system
set /p PI_USER="Enter Raspberry Pi Username (default: predator_alert_system): "

echo.
echo Copying files to %PI_USER%@%PI_IP%:/home/%PI_USER%/predator_alert...
echo (You may be asked for your Raspberry Pi password)
echo.

ssh %PI_USER%@%PI_IP% "rm -rf /home/%PI_USER%/predator_alert"
scp -r . %PI_USER%@%PI_IP%:/home/%PI_USER%/predator_alert

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [SUCCESS] Files transferred successfully!
    echo.
    echo NEXT STEPS:
    echo 1. On your Pi (VNC/SSH), run: cd ~/predator_alert
    echo 2. Install requirements: pip install -r requirements.txt
    echo 3. Run the app: python main.py
) else (
    echo.
    echo [ERROR] Transfer failed. Please check the IP and try again.
)

pause
