FROM python:3.12-slim

WORKDIR /app
COPY brain/ /app/
COPY brain/requirements.txt /app/

RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

CMD ["python", "-m", "brain.manager"]
