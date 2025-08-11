# Full-stack Docker image (React + FastAPI)

# Stage 1: Build React frontend
FROM node:18-alpine as frontend-build

WORKDIR /app/frontend

# Copy package files
COPY frontend/package*.json ./

# Install dependencies
RUN npm ci

# Copy source code and build
COPY frontend/ ./
RUN npm run build

# Stage 2: Python backend with React static files
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ ./backend/
COPY llm/ ./llm/

# Copy React build from frontend stage - flatten structure
COPY --from=frontend-build /app/frontend/build/ ./backend/static/
RUN if [ -d "/app/backend/static/static" ]; then \
      cp -r /app/backend/static/static/* /app/backend/static/ && \
      rm -rf /app/backend/static/static; \
    fi

# Copy image files from frontend public directory
COPY --from=frontend-build /app/frontend/public/img/ ./backend/static/img/

# Set Python path
ENV PYTHONPATH=/app:/app/backend:/app/llm

# Expose the port
EXPOSE 8000

# Run the application
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]