# syntax=docker/dockerfile:1.4

# Establish a base stage for common setup tasks
FROM python:3.9-slim as base

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY req.txt /app

# Install Python dependencies

RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install streamlit==1.41.1
RUN pip install --no-cache-dir -r req.txt

# Testing
FROM base AS testing
WORKDIR /app

COPY req_tests.txt /app

RUN pip install coverage==7.3.2 pytest==7.4.3 pytest-mock==3.14.0
RUN pip install --no-cache-dir -r req_tests.txt

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

