# Dockerfile for setting up Ghidra Codespace environment with XFCE and noVNC
FROM mcr.microsoft.com/devcontainers/base:ubuntu

# Install necessary packages
RUN apt-get update && apt-get install -y \
    xfce4 xfce4-goodies x11vnc novnc xvfb sudo curl wget git \
    && apt-get clean

# Add a non-root user with sudo privileges
ARG USER=codespace
RUN useradd -m -s /bin/bash $USER && echo "$USER ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Set environment variables for X11 and VNC
ENV DISPLAY=:99
ENV DEBIAN_FRONTEND=noninteractive

# Configure permissions and directories
RUN mkdir -p /mnt/data /root/.vnc /home/$USER/.vnc \
    && chmod 1777 /tmp/.X11-unix \
    && chown -R $USER:$USER /mnt/data /home/$USER/.vnc

# Set the user
USER $USER

# Expose necessary ports for VNC and noVNC
EXPOSE 5901 6080