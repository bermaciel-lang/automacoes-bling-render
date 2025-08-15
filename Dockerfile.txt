FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium chromium-driver fonts-liberation tzdata ca-certificates \
    && rm -rf /var/lib/apt/lists/*

ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER=/usr/bin/chromedriver
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Acelera pip/wheels
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

COPY requirements.txt /app/requirements.txt
# força usar wheels quando disponíveis
RUN pip install --no-cache-dir --only-binary=:all: -r requirements.txt

COPY . /app

CMD ["python", "main.py"]
