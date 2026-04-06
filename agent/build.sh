#!/bin/bash

# Build script for SSD Agent on Linux
# To run: chmod +x build.sh && ./build.sh

echo "Starting build process for SSD Agent..."

# Install dependencies
pip install -r requirements.txt

# Create the binary
pyinstaller --name=ssd-agent \
    --onefile \
    --clean \
    --add-data="collectors:collectors" \
    --add-data="executor:executor" \
    --add-data="config.py:." \
    --hidden-import=flask \
    --hidden-import=psutil \
    agent_server.py

echo "Build completed!"
echo "Binary is located at: dist/ssd-agent"