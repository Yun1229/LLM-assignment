# Use an official Python runtime as a base image
FROM python:3.12.0

# Set the working directory in the container
WORKDIR /project

# Copy the requirements file into the container
COPY requirements.txt .

# Install any dependencies specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Command to run the application
CMD ["python", "build_db.py"]
