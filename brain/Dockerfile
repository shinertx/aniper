FROM python:3.12-slim

WORKDIR /app

# 1. Install dependencies first for cache
COPY brain/requirements.txt /app/
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# 2. Copy the rest of the code
COPY brain/ /app/

CMD ["python", "-m", "manager"]
