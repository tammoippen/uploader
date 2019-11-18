FROM python:3.7-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    VIRTUAL_ENV=/venv \
    LOGURU_LEVEL=INFO \
	LOGURU_DIAGNOSE=False

RUN apt-get update && apt-get install -y \
    curl \
 && curl -sSL https://raw.githubusercontent.com/sdispater/poetry/master/get-poetry.py | python \
 && apt-get remove -y curl \
 && apt-get autoremove -y \
 && rm -rf /var/lib/apt/lists/* \
 && python -m venv $VIRTUAL_ENV

ENV PATH=$VIRTUAL_ENV/bin:/root/.poetry/bin:$PATH

# install dependencies
COPY pyproject.toml ./
RUN apt-get update && apt-get install -y \
    build-essential \
 && poetry install -E gcs -n --no-dev \
 && apt-get remove -y build-essential \
 && apt-get autoremove -y \
 && rm -rf /var/lib/apt/lists/* \
 && rm -rf /root/.cache/pip

# need second install after copy to actually get
# project installed
COPY . .
RUN poetry install -E gcs -n --no-dev

EXPOSE 80

ENTRYPOINT [ "uvicorn", "uploader:app", "--host", "0.0.0.0", "--port", "80" ]
