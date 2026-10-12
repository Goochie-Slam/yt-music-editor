@echo off
rem YT Music Editor - developer launcher for Windows (M1).
rem The end-user portable bundle (no uv / Node needed) comes in M7.
setlocal
cd /d "%~dp0\..\.."
set "ROOT=%CD%"

where uv >nul 2>nul || (
  echo [!] Can cai uv: mo PowerShell va chay:
  echo     powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  pause & exit /b 1
)

if not exist "backend\bin" mkdir "backend\bin"

if not exist "backend\bin\ffmpeg.exe" (
  where ffmpeg >nul 2>nul || (
    echo Dang tai FFmpeg ^(khoang 100 MB^)...
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
      "$ProgressPreference='SilentlyContinue';" ^
      "Invoke-WebRequest 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip' -OutFile ffmpeg.zip;" ^
      "Expand-Archive ffmpeg.zip -DestinationPath ffmpeg_tmp -Force;" ^
      "$bin = Get-ChildItem ffmpeg_tmp -Recurse -Filter ffmpeg.exe | Select-Object -First 1;" ^
      "Copy-Item $bin.FullName, (Join-Path $bin.DirectoryName 'ffprobe.exe') 'backend\bin\';" ^
      "Remove-Item ffmpeg.zip; Remove-Item ffmpeg_tmp -Recurse"
  )
)

if not exist "backend\bin\yt-dlp.exe" (
  echo Dang tai yt-dlp...
  powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$ProgressPreference='SilentlyContinue';" ^
    "Invoke-WebRequest 'https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe' -OutFile 'backend\bin\yt-dlp.exe'"
)

if not exist "frontend\dist\index.html" (
  where npm >nul 2>nul || (
    echo [!] Can cai Node.js 22 LTS de build giao dien: https://nodejs.org/
    pause & exit /b 1
  )
  pushd frontend
  call npm ci || (popd & pause & exit /b 1)
  call npm run build || (popd & pause & exit /b 1)
  popd
)

cd backend
uv sync --locked || (pause & exit /b 1)
echo Dang mo YT Music Editor tai http://127.0.0.1:8765/  ^(dong cua so nay de tat app^)
uv run python -m app.main
pause
