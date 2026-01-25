@echo off
echo Compiling CSS with Tailwind + DaisyUI...
cd web\static\css
build\tailwindcss.exe -i src\input.css -o dist\styles.css --minify
echo CSS compiled to dist\styles.css
