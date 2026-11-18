FROM python:3.12-slim

# Node.js 20 (needed to build the React app)
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
 && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
 && apt-get install -y --no-install-recommends nodejs \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

# 1) Python deps
RUN pip install --no-cache-dir -r backend/requirements.txt

# 2) Build React -> creates /app/frontend/dist  (exactly where main.py looks)
WORKDIR /app/frontend
RUN npm install && npm run build

# 3) Run the API from backend so `app.main` is importable
WORKDIR /app/backend
ENV PYTHONPATH=/app/backend
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]