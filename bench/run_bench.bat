@echo off
rem YT Music Editor - render benchmark (Spike S1). Double-click to run.
setlocal
cd /d "%~dp0"

where py >nul 2>nul && (set "PY=py -3.12") || (set "PY=python")
%PY% --version >nul 2>nul || (
  echo [!] Can cai Python 3.12: https://www.python.org/downloads/  ^(tick "Add python.exe to PATH"^)
  pause & exit /b 1
)

if not exist "ffmpeg\bin\ffmpeg.exe" (
  where ffmpeg >nul 2>nul || (
    echo Dang tai FFmpeg ^(khoang 100 MB^)...
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
      "$ProgressPreference='SilentlyContinue';" ^
      "Invoke-WebRequest 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip' -OutFile ffmpeg.zip;" ^
      "Expand-Archive ffmpeg.zip -DestinationPath ffmpeg_tmp -Force;" ^
      "$d = Get-ChildItem ffmpeg_tmp -Directory | Select-Object -First 1;" ^
      "Move-Item $d.FullName ffmpeg; Remove-Item ffmpeg.zip; Remove-Item ffmpeg_tmp -Recurse"
    if not exist "ffmpeg\bin\ffmpeg.exe" (
      echo [!] Tai FFmpeg that bai. Tai tay tu https://www.gyan.dev/ffmpeg/builds/ va giai nen vao bench\ffmpeg
      pause & exit /b 1
    )
  )
)

if not exist ".venv\Scripts\python.exe" %PY% -m venv .venv
".venv\Scripts\python.exe" -m pip install -q --disable-pip-version-check -r requirements.txt || (
  echo [!] Cai thu vien Python that bai. & pause & exit /b 1
)

".venv\Scripts\python.exe" run_bench.py %*
echo.
echo Xong. Gui toan bo thu muc bench\results cho Claude.
pause
