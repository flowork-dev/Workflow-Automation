# Di dalam: flowork-gateway/Dockerfile
# (MODIFIED) Corrected PYTHONPATH to include flowork-core

# Base image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    sqlite3 \
    libsqlite3-dev \
    build-essential \
    cmake \
    libportaudio2 \
    portaudio19-dev \
    && rm -rf /var/lib/apt/lists/*

# [MODIFIED] Add both /app (for gateway) AND /app/flowork-core (for kernel) to PYTHONPATH
ENV PYTHONPATH="/app:/app/flowork-core:${PYTHONPATH}"

# Create directories for persistent data (mounted via volumes)
RUN mkdir -p /app/data
RUN mkdir -p /app/core-data

# Copy requirements first to leverage Docker cache
COPY ./flowork-gateway/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy the core library code into the container
COPY ./flowork-core/ /app/flowork-core/

# Copy the rest of the gateway application code
COPY ./flowork-gateway/ /app/

# Expose the port the app runs on
EXPOSE 8000

# Run the entrypoint script which handles migrations and starts the server
ENTRYPOINT ["/app/entrypoint.sh"]

# Default command to start the application using uvicorn
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]