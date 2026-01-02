FROM python:3.11-slim

# Install system dependencies including Docker CLI and PAM (from Debian repo)
RUN apt-get update && apt-get install -y --no-install-recommends \
    procps \
    curl \
    iproute2 \
    libpam0g-dev \
    libcrypt1 \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir psutil python-pam six

# Create app directory
WORKDIR /app

# Copy application files
COPY index.html /app/
COPY stats_api.py /app/
COPY scrypted_stats.py /app/

# Expose port
EXPOSE 8080

# Run the server with unbuffered output
CMD ["python3", "-u", "stats_api.py"]
