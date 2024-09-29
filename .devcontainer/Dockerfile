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

# Set locale environment to avoid warnings
RUN locale-gen en_US.UTF-8 && \
    update-locale LANG=en_US.UTF-8 LANGUAGE=en_US:en LC_ALL=en_US.UTF-8
ENV LANG=en_US.UTF-8 \
    LANGUAGE=en_US:en \
    LC_ALL=en_US.UTF-8

# Revert DEBIAN_FRONTEND to prevent issues in interactive shells later (optional)
ENV DEBIAN_FRONTEND=noninteractive

# Create a non-root user with sudo privileges
ARG USER=codespace
RUN id -u $USER 2>/dev/null || useradd -m -s /bin/bash $USER && \
    echo "$USER ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Set environment variables for X11 and VNC
ENV DISPLAY=:99

# Set up .vnc directory and permissions for the new user
RUN mkdir -p /mnt/data /home/$USER/.vnc /home/$USER/.config && \
    echo "yourpassword" | vncpasswd -f > /home/$USER/.vnc/passwd && \
    chmod 600 /home/$USER/.vnc/passwd && \
    chmod 1777 /tmp/.X11-unix && \
    chown -R $USER:$USER /mnt/data /home/$USER/.vnc /home/$USER/.config

# Add entry point script (optional)
COPY setup_novnc.sh /home/$USER/setup_novnc.sh
RUN chmod +x /home/$USER/setup_novnc.sh

# Set the user to non-root
USER $USER

# Expose necessary ports for VNC and noVNC
EXPOSE 5901 6080

# Default command to run XFCE and noVNC setup
CMD ["bash", "/home/codespace/setup_novnc.sh"]
