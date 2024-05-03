FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
    gcc libgl1 libglib2.0-0\
    && rm -rf /var/lib/apt/lists/*

WORKDIR /fastapi

COPY requirements.txt /fastapi

RUN pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
RUN pip install -r requirements.txt

COPY . /fastapi

EXPOSE 8000

CMD hypercorn server:app --bind '[::]:8000'
# hypercorn allows dual stack IPv4/IPv6 binding
