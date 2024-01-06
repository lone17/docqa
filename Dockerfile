# Use the official Python base image
FROM python:3.10

# Set the working directory inside the container
WORKDIR /code

# Setup for marker (following its README)
RUN wget https://github.com/ArtifexSoftware/ghostpdl-downloads/releases/download/gs10012/ghostscript-10.01.2.tar.gz && \
    tar -xvf ghostscript-10.01.2.tar.gz && \
    cd ghostscript-10.01.2 && \
    ./configure && \
    make install && \
    cd .. && \
    rm -rf ghostscript-10.01.2 && \
    rm ghostscript-10.01.2.tar.gz

RUN apt-get update && \
    apt-get install -y tesseract-ocr libtesseract-dev libmagic1 ocrmypdf

# Copy marker and install it
COPY ./marker /code/marker
WORKDIR /code/marker
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
