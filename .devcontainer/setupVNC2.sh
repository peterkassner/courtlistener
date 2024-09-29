#!/bin/bash

# Ensure the script is run with sudo privileges
if [ "$(id -u)" -ne 0 ]; then
  echo "Please run this script as root (e.g., sudo ./setup_novnc.sh)"
  exit 1
fi

echo "===================="
echo "Installing XFCE4, Xvfb, and x11vnc..."
echo "===================="

# Install XFCE, Xvfb, x11vnc, and noVNC
sudo apt-get update && sudo apt-get install -y xfce4 xfce4-goodies x11vnc novnc xvfb

# Check if the installation was successful
if ! command -v x11vnc &> /dev/null; then
  echo "Error: x11vnc installation failed. Please check your package manager or internet connection."
  exit 1
fi

# Remove stale lock files if any (from previous sessions)
sudo rm -f /tmp/.X99-lock /tmp/.X11-unix/X99

echo "===================="
echo "Starting a virtual X server with Xvfb on display :99..."
echo "===================="

# Start a virtual X server on display :99 with clean configurations
Xvfb :99 -screen 0 1280x1024x24 +extension GLX -ac -noreset -nolisten tcp -nolisten unix &
XVFB_PID=$!

# Wait for Xvfb to initialize
sleep 5

# Set the DISPLAY environment variable to use the virtual display
export DISPLAY=:99

echo "===================="
echo "Configuring XFCE4 session..."
echo "===================="

# Start the XFCE4 session manager in the background
startxfce4 &

# Wait for XFCE to start properly
sleep 10

# Create a VNC password file (optional step)
mkdir -p ~/.vnc
x11vnc -storepasswd yourpassword ~/.vnc/passwd

echo "===================="
echo "Configuring x11vnc on display :99..."
echo "===================="

# Start x11vnc server on display :99, port 5901 with ideal configurations
x11vnc -display :99 -forever -shared -rfbport 5901 -bg -rfbauth ~/.vnc/passwd -noxdamage -ncache 10 -cursor arrow -xkb -graball -quiet
echo "x11vnc server started on display :99, port 5901"

echo "===================="
echo "Configuring noVNC..."
echo "===================="

# Start noVNC server and forward VNC traffic from port 5901
/usr/share/novnc/utils/launch.sh --vnc localhost:5901 --listen 6080 &
NOVNC_PID=$!

# Give a few seconds for the noVNC server to start
sleep 5

echo "===================="
echo "Ports Exposed:"
echo " - VNC Port: 5901"
echo " - noVNC Web Port: 6080"
echo "===================="

# Display next steps to the user
echo "===================="
echo "Instructions:"
echo "1. In your Codespace settings, expose the noVNC port (6080)."
echo "2. After exposing the port, access the following URL in your browser:"
echo "   http://localhost:6080/vnc.html"
echo "===================="

# Check if the necessary processes are running
if ps -p $XVFB_PID > /dev/null && ps -p $NOVNC_PID > /dev/null && pgrep -x "x11vnc" > /dev/null; then
  echo "Setup completed successfully. You can now connect to your Ghidra GUI using the provided noVNC URL."
else
  echo "Something went wrong. Please check if Xvfb, x11vnc, and noVNC are running."
fi

# Optional: Provide a cleanup script or instructions
echo "To stop the servers, you can use the following commands:"
echo " - sudo pkill x11vnc"
echo " - sudo pkill websockify"
echo " - sudo pkill Xvfb"
echo " - sudo pkill xfwm4"