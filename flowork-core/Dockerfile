#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\Dockerfile
# REPAIRED VERSION - Multi-Stage Build + Added curl for Healthcheck
#######################################################################

# --- Stage 1: The Builder ---
# This stage has all the tools needed to compile heavy libraries.
FROM python:3.11-slim as builder

# Set the working directory
WORKDIR /app

# (ADDED CODE) Install system dependencies required for compilation
# build-essential includes gcc, g++, make, etc.
# cmake is required by llama-cpp-python
# portaudio19-dev is required by pyaudio
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    portaudio19-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy the dependency file
COPY requirements.txt .

# Install all python packages into a virtual environment inside this stage
# This leverages the build tools we just installed
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir -r requirements.txt


# --- Stage 2: The Final Image ---
# This stage is clean and slim, only containing what's needed to run.
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# (PENAMBAHAN KODE UNTUK HEALTH CHECK - ATURAN EMAS #5 TIDAK BERLAKU KARENA INI PAKET SISTEM) Install curl
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# (ADDED CODE) Copy the installed python packages from the builder stage
COPY --from=builder /opt/venv /opt/venv

# (ADDED CODE) Copy the application code
COPY . .

# Activate the virtual environment for subsequent commands
ENV PATH="/opt/venv/bin:$PATH"

# Expose the ports for the main API server and the dashboard
EXPOSE 8989
EXPOSE 5001

# Define the command to run the application
CMD ["python", "run_server.py"]