FROM python:3.10.4-slim

COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt
RUN apt-get update \
  && apt-get install -y --no-install-recommends git git-lfs curl \
  && apt-get purge -y --auto-remove \
  && rm -rf /var/lib/apt/lists/*

ENTRYPOINT ./config.sh || true
