# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /code

# Copy the application code and requirements
COPY ./app /code/app
COPY ./requirements.txt /code/

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Set Python path
ENV PYTHONPATH=/code
EXPOSE 8080
# Cloud Run will set PORT environment variable (typically 8080)
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}
