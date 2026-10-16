# syntax=docker/dockerfile:1

# Build an image with the Python 3.12 image
FROM python:3.12-alpine

# Set the working directory to `/code`
WORKDIR /code

# Install `gcc` and other dependencies
RUN apk add --no-cache gcc musl-dev linux-headers

# Copy `requirements.txt`
COPY requirements.txt .

# Install the Python dependencies
RUN pip install -r requirements.txt

# Copy the current directory `.` in the project to the workdir `.` in the image
COPY . .

ENV REDIS_HOST=10.10.0.116
ENV REDIS_PORT=6379

EXPOSE 5000

# Set the default command for the container to `flask run --debug`

CMD ["fastapi", "run", "app.py", "--host", "0.0.0.0", "--port", "5000"]

