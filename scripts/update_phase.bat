@echo off
REM ================================================================
REM XMMCG CompetitionPhase Status Auto-Update Script
REM 自动更新比赛阶段状态
REM ================================================================

REM 切换到项目目录
cd /d C:\Users\fengy\xmmcg-net\backend\xmmcg

REM 激活虚拟环境
call C:\Users\fengy\xmmcg-net\.venv\Scripts\activate.bat

REM 执行更新命令并记录日志
echo [%date% %time%] Starting phase status update... >> C:\Users\fengy\xmmcg-net\logs\phase_update.log
python manage.py update_phase_status >> C:\Users\fengy\xmmcg-net\logs\phase_update.log 2>&1
echo [%date% %time%] Phase status update completed. >> C:\Users\fengy\xmmcg-net\logs\phase_update.log
echo. >> C:\Users\fengy\xmmcg-net\logs\phase_update.log
