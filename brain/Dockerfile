FROM python:3.12-slim

WORKDIR /app

# 1. Install dependencies first for cache
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# 2. Copy the rest of the code
COPY . /app/

# Optional: use a non-root user for security
# RUN useradd -m appuser && chown -R appuser /app
# USER appuser

# Optional: expose port if you add an API/metrics endpoint in the future
# EXPOSE 8000

CMD ["python", "-m", "manager"]
