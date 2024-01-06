# Use the official Python base image
FROM python:3.10

# Set the working directory inside the container
WORKDIR /code

# Copy marker and install it (following its README)
COPY ./marker /code/marker
WORKDIR /code/marker
RUN chmod +x ./scripts/install/ghostscript_install.sh && \
    ./scripts/install/ghostscript_install.sh
RUN apt-get update && \
    cat ./scripts/install/apt-requirements.txt | xargs apt-get install -y
RUN pip install .

# Back to main working directory
WORKDIR /code

# Download models, need to install angle-emb here for the embedding model
RUN pip install angle-emb
COPY ./download_models.py /code/
RUN python download_models.py

# Copy requirements files to the working directory
COPY ./requirements.txt /code/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code to the working directory
COPY . /code/

# Install the docqa package
RUN pip install .

# For documentation
EXPOSE 8000

# Command to run the FastAPI application using uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
