FROM python:3.11

WORKDIR /Fw

COPY . /Fw

RUN pip install -r requirements.txt
