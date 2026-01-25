@echo off
echo Downloading Tailwind CSS and DaisyUI build tools...

REM Create build directory
if not exist "web\static\css\build" mkdir web\static\css\build

REM Download Tailwind CLI
echo Downloading Tailwind CSS CLI...
powershell -Command "Invoke-WebRequest -Uri 'https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-windows-x64.exe' -OutFile 'web\static\css\build\tailwindcss.exe'"

REM Download DaisyUI plugins
echo Downloading DaisyUI plugins...
powershell -Command "Invoke-WebRequest -Uri 'https://github.com/saadeghi/daisyui/releases/latest/download/daisyui.mjs' -OutFile 'web\static\css\build\daisyui.mjs'"
powershell -Command "Invoke-WebRequest -Uri 'https://github.com/saadeghi/daisyui/releases/latest/download/daisyui-theme.mjs' -OutFile 'web\static\css\build\daisyui-theme.mjs'"

echo.
echo Build tools downloaded successfully!
echo Run build-css.bat to compile CSS.
