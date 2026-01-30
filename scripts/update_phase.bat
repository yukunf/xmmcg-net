@echo off
REM ================================================================
REM XMMCG CompetitionPhase Status Auto-Update Script
REM 自动更新比赛阶段状态
REM ================================================================

REM 设置项目根目录为当前脚本所在目录的上一级目录
set "PROJECT_ROOT=%~dp0.."

REM 切换到项目目录
cd /d "%PROJECT_ROOT%\backend\xmmcg"

REM 激活虚拟环境
call "%PROJECT_ROOT%\.venv\Scripts\activate.bat"

REM 执行更新命令并记录日志
set "LOG_FILE=%PROJECT_ROOT%\logs\phase_update.log"
echo [%date% %time%] Starting phase status update... >> "%LOG_FILE%"
python manage.py update_phase_status >> "%LOG_FILE%" 2>&1
echo [%date% %time%] Phase status update completed. >> "%LOG_FILE%"
echo. >> "%LOG_FILE%"
