# Use an official Python runtime as a parent image
FROM python:3.11-slim-buster

# Set the working directory in the container
WORKDIR /app

# Copy the dependencies file first to leverage Docker cache
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
ARG CACHEBUST=1
RUN pip install --no-cache-dir -r requirements.txt


# Copy the rest of the application code
COPY . .

# Make port 5672 available to the world outside this container
EXPOSE 5672

# Run main.py when the container launches
CMD ["python", "main.py"]