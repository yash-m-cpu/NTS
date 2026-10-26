FROM python:3.12-slim

# Install uv
RUN pip install uv

WORKDIR /app

# Copy dependency files first
COPY pyproject.toml uv.lock ./

# Install dependencies via uv
RUN uv sync --frozen --no-install-project

# Install system deps: ffmpeg, curl, Node.js 20, OpenCV system libs, and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg curl python3-dev build-essential \
        libgl1 libglib2.0-0 \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js CV dependencies at container level (compiled for Linux)
# @tensorflow/tfjs-node is a native module that must be compiled in the target OS
RUN mkdir -p /cv-node-modules && \
    cd /cv-node-modules && \
    npm init -y && \
    npm install @tensorflow/tfjs-node pipe2jpeg --prefer-offline

# Copy the rest of the application code
COPY . .

# Ensure PYTHONPATH includes the app directory and PATH includes venv
ENV PYTHONPATH=/app
ENV PATH="/app/.venv/bin:$PATH"
# Node modules compiled for Linux — accessible via NODE_PATH
ENV NODE_PATH=/cv-node-modules/node_modules

CMD ["python", "scripts/run_worker.py"]
