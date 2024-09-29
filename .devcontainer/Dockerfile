# Dockerfile for setting up Ghidra Codespace environment with XFCE and noVNC
FROM mcr.microsoft.com/devcontainers/base:ubuntu:20.04

# Set environment variable to disable interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install necessary packages and configure keyboard settings
RUN apt-get update && \
    echo 'keyboard-configuration keyboard-configuration/layoutcode select us' | debconf-set-selections && \
    echo 'keyboard-configuration keyboard-configuration/modelcode select pc105' | debconf-set-selections && \
    apt-get install -y \
    xfce4 xfce4-goodies x11vnc novnc xvfb sudo curl wget git locales keyboard-configuration console-setup \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Revert DEBIAN_FRONTEND to dialog mode to prevent unexpected behavior
ENV DEBIAN_FRONTEND=dialog

# Add a non-root user with sudo privileges
ARG USER=codespace
RUN id -u $USER 2>/dev/null || useradd -m -s /bin/bash $USER && \
    echo "$USER ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Set environment variables for X11 and VNC
ENV DISPLAY=:99

# Configure permissions and directories
RUN mkdir -p /mnt/data /root/.vnc /home/$USER/.vnc && \
    chmod 1777 /tmp/.X11-unix && \
    chown -R $USER:$USER /mnt/data /home/$USER/.vnc

# Set the user
USER $USER

# Expose necessary ports for VNC and noVNC
EXPOSE 5901 6080
