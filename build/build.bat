@echo off
rem Build check for Claude: compiles the project from the command line and compares warnings with a baseline.
rem Does not touch the developer's exe / dcu files: output goes to out\ and logs to log\ under this folder.
rem Usage:  build.bat            build + compare with the baseline
rem         build.bat baseline   build + save this build's warnings as the baseline
rem Settings (can be overridden with environment variables):
rem   DELPHI_RSVARS   path of rsvars.bat (depends on the Delphi version)
rem   DELPHI_DPROJ    the .dproj to build (relative to this folder or absolute)
rem   DELPHI_CONFIG   Debug / Release      DELPHI_PLATFORM  Win32 / Win64
rem Note: this file must keep CRLF line endings (with LF, cmd swallows the start of lines).
chcp 65001 >nul
setlocal
set "D=%~dp0"
if not defined DELPHI_RSVARS set "DELPHI_RSVARS=C:\Program Files (x86)\Embarcadero\Studio\37.0\bin\rsvars.bat"
if not defined DELPHI_DPROJ set "DELPHI_DPROJ=%D%..\Project.dproj"
if not defined DELPHI_CONFIG set "DELPHI_CONFIG=Debug"
if not defined DELPHI_PLATFORM set "DELPHI_PLATFORM=Win32"
call "%DELPHI_RSVARS%"
if not exist "%D%out\exe" mkdir "%D%out\exe"
if not exist "%D%out\dcu" mkdir "%D%out\dcu"
if not exist "%D%log" mkdir "%D%log"
rem Do NOT use /clp:Summary: it repeats every warning in the summary and doubles the count.
msbuild "%DELPHI_DPROJ%" /t:Build /p:Config=%DELPHI_CONFIG% /p:Platform=%DELPHI_PLATFORM% "/p:DCC_ExeOutput=%D%out\exe" "/p:DCC_DcuOutput=%D%out\dcu" /nologo /v:minimal > "%D%log\last.log" 2>&1
set RC=%ERRORLEVEL%
python -I "%D%summary.py" "%D%log\last.log" "%D%log\baseline.txt" %RC% %1
exit /b %RC%
