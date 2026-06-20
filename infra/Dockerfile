FROM python:3.11-slim as builder
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

ENV PYTHONUNBUFFERED=1
COPY . /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
WORKDIR /app
FROM python:3.11-slim

RUN pip install --no-cache-dir -r requirements.txt
COPY requirements.txt /app/
# Install pip and dependencies directly from requirements.txt for simplicity

COPY pyproject.toml poetry.lock* /app/

  && rm -rf /var/lib/apt/lists/*
    curl \
    libpq-dev \
    gcc \
    git \
    build-essential \
RUN apt-get update && apt-get install -y --no-install-recommends \
# Install build deps

WORKDIR /app

