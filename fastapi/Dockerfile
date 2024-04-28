FROM python:3.10-slim

RUN mkdir /fastapi

COPY requirements.txt /fastapi

WORKDIR /fastapi

RUN pip install -r requirements.txt

COPY . /fastapi

EXPOSE 8000

CMD hypercorn server:app --bind '[::]:8000'
#switching to hypercorn from uvicorn to allow dualstack binding
