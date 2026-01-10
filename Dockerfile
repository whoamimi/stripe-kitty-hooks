# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /code

# Copy requirements first for better layer caching
COPY ./requirements.txt /code/

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY ./app /code/app

# Set Python path
ENV PYTHONPATH=/code

# Expose port (Cloud Run will override with PORT env var)
EXPOSE 8080

# Run the application
# Cloud Run will set PORT environment variable (typically 8080)
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}
