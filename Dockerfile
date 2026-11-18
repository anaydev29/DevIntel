# 1. Use Python 3.12 slim image
FROM python:3.12-slim

# 2. Install Node.js 20 for building the frontend
RUN apt-get update && apt-get install -y curl
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
RUN apt-get install -y nodejs

# 3. Set working directory
WORKDIR /app

# 4. Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Build the Frontend
COPY frontend/package*.json ./frontend/
WORKDIR /app/frontend
RUN npm install
RUN npm run build

# 6. Copy Backend Code
WORKDIR /app
COPY backend/ ./backend/

# 7. Move the built frontend into the backend directory so FastAPI can serve it
# (Adjust 'frontend_dist' if your main.py expects a different folder name)
RUN mkdir -p backend/frontend_dist
RUN cp -r frontend/dist/* backend/frontend_dist/

# 8. Set environment and start the server
ENV PYTHONPATH=/app/backend
WORKDIR /app/backend

# Render/Railway use the PORT environment variable
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}