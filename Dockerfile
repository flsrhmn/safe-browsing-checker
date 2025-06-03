# Updated Dockerfile for web server wrapper
FROM python:3.11-slim

# Install a tiny web server
RUN pip install flask

# Copy files
WORKDIR /app
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create health check endpoint
RUN echo "from flask import Flask; app = Flask(__name__)" > healthcheck.py
RUN echo "@app.route('/')" >> healthcheck.py
RUN echo "def health(): return 'OK'" >> healthcheck.py

# Start script
CMD ["sh", "-c", "python healthcheck.py & python main.py"]
