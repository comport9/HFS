@echo off
REM Double-click this to run HFS.
REM Runs from this folder (so it finds heart.png / newtalent.png / HFS.ico) and
REM pauses if there's an error, so you can actually read it.
cd /d "%~dp0"
py "%~dp0HFS.py"
if errorlevel 1 pause
