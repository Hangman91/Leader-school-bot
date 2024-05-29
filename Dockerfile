FROM python:3.7-slim

COPY requirements.txt requirements.txt
RUN pip3 install --upgrade setuptools
RUN pip3 install -r requirements.txt

COPY leaderschoolbot/ /app
WORKDIR /app
ENV PYTHONUNBUFFERED=1
