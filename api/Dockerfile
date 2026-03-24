FROM python:3.11.9-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

# scraper package is mounted at /scraper via docker-compose volume
ENV PYTHONPATH="/scraper:${PYTHONPATH}"

COPY . .
