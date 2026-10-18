@echo off
setlocal
cd /d "%~dp0"

set "BUILD_PYTHON=%~dp0.venv-build\Scripts\python.exe"

where python >nul 2>&1
if errorlevel 1 goto :python_missing

if not exist "%BUILD_PYTHON%" (
    echo Creating build environment...
    python -m venv "%~dp0.venv-build"
    if errorlevel 1 goto :build_failed
)

echo Installing build requirements...
"%BUILD_PYTHON%" -m pip install -r "%~dp0build-requirements.txt"
if errorlevel 1 goto :build_failed

echo Building Jazz Chord Voicer...
"%BUILD_PYTHON%" -m PyInstaller --noconfirm --clean "%~dp0jazzChordVoicer.spec"
if errorlevel 1 goto :build_failed

if not exist "%~dp0dist\JazzChordVoicer\JazzChordVoicer.exe" goto :build_failed

echo Creating portable ZIP...
"%BUILD_PYTHON%" -c "import shutil; shutil.make_archive(r'%~dp0dist\JazzChordVoicer-windows', 'zip', root_dir=r'%~dp0dist', base_dir='JazzChordVoicer')"
if errorlevel 1 goto :build_failed

echo.
echo Build complete.
echo App: %~dp0dist\JazzChordVoicer\JazzChordVoicer.exe
echo Shareable ZIP: %~dp0dist\JazzChordVoicer-windows.zip
if /i "%~1"=="--no-pause" exit /b 0
pause
exit /b 0

:python_missing
echo Python was not found. Install Python 3 and ensure it is available as "python".
goto :failure

:build_failed
echo.
echo The build did not complete. Review the error above and try again.

:failure
set "BUILD_EXIT_CODE=%ERRORLEVEL%"
if "%BUILD_EXIT_CODE%"=="0" set "BUILD_EXIT_CODE=1"
if /i "%~1"=="--no-pause" exit /b %BUILD_EXIT_CODE%
pause
exit /b %BUILD_EXIT_CODE%
