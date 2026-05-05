@echo off
setlocal
set "script_dir=%~dp0"
for %%I in ("%script_dir%..") do set "repo_root=%%~fI"
if not defined THESIS_REVIEW_CALLER_CWD set "THESIS_REVIEW_CALLER_CWD=%CD%"
set "PYTHONPATH=%repo_root%\src"
cd /d "%repo_root%" || exit /b 1
if defined WORKFLOW_TOOLS_PYTHON goto use_env_python
py -3.12 -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 1)" >nul 2>nul
if not errorlevel 1 goto use_py_launcher
python -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 1)" >nul 2>nul
if not errorlevel 1 goto use_python_launcher
goto python_error

:use_env_python
"%WORKFLOW_TOOLS_PYTHON%" -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 1)" >nul 2>nul
if errorlevel 1 goto python_error
"%WORKFLOW_TOOLS_PYTHON%" -m thesis_review_workflow.cli.package_workflow_tools %*
exit /b %ERRORLEVEL%

:use_py_launcher
py -3.12 -m thesis_review_workflow.cli.package_workflow_tools %*
exit /b %ERRORLEVEL%

:use_python_launcher
python -m thesis_review_workflow.cli.package_workflow_tools %*
exit /b %ERRORLEVEL%

:python_error
echo Workflow tool packaging requires Python 3.12. Set WORKFLOW_TOOLS_PYTHON=C:\Path\To\python.exe if needed. 1>&2
exit /b 1
