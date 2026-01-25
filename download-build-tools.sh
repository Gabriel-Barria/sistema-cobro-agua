#!/bin/bash
echo "Downloading Tailwind CSS and DaisyUI build tools..."

# Create build directory
mkdir -p web/static/css/build

# Download Tailwind CLI
echo "Downloading Tailwind CSS CLI..."
curl -sLo web/static/css/build/tailwindcss https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-linux-x64
chmod +x web/static/css/build/tailwindcss

# Download DaisyUI plugins
echo "Downloading DaisyUI plugins..."
curl -sLo web/static/css/build/daisyui.mjs https://github.com/saadeghi/daisyui/releases/latest/download/daisyui.mjs
curl -sLo web/static/css/build/daisyui-theme.mjs https://github.com/saadeghi/daisyui/releases/latest/download/daisyui-theme.mjs

echo ""
echo "Build tools downloaded successfully!"
echo "Run ./build-css.sh to compile CSS."
