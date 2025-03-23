# syntax=docker/dockerfile:1.4

FROM python:3.9-slim as base

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY docker/req.txt /app/
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install streamlit==1.41.1
RUN pip install --no-cache-dir -r req.txt

# Testing stage
FROM base AS testing
WORKDIR /app

COPY docker/req_tests.txt /app/
RUN pip install --no-cache-dir -r req_tests.txt

# Copy the entire project structure
COPY . /app

# Install the package in development mode
WORKDIR /app/apps/todo
RUN pip install -e .

WORKDIR /app
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

