# Use official Python image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    GOOGLE_CLOUD_PROJECT=safe-browsing-check-461816

# Install dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy files
WORKDIR /app
COPY . .

# Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Run the script
CMD ["python", "main.py"]
