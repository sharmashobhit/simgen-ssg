
# Use an official Python runtime as a parent image
FROM python:3.9-slim-buster

# Set the working directory to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in package
RUN pip install -e .

# Expose port 8000 for the Flask app to run on
EXPOSE 8000

# RUN mkdir -p /content/

# # Run the command to start the server
RUN ["simgen", "fetch-model"]

CMD [ "simgen", "serve", "--dir", "/docs/", "--bind", "0.0.0.0:8000", "--watch" ]