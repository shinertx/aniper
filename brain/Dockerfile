FROM python:3.11-slim

WORKDIR /app
COPY brain/ /app/
COPY brain/requirements.txt /app/

RUN pip install --upgrade pip && pip install -r requirements.txt

CMD ["python", "-m", "brain.manager"]
