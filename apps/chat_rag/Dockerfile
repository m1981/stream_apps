# Start from a base image
FROM python:3.11-slim

RUN apt-get update --fix-missing && apt-get install -y --fix-missing build-essential

# Set a directory for the app
WORKDIR /usr/src/app

# Copy all the files to the container
COPY . .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt