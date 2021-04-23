#################
# Build container
FROM python:3.8-slim as build

RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

ENV POETRY_HOME="/opt/poetry"

RUN curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python -

ENV PATH="$POETRY_HOME/bin:$PATH"

WORKDIR /app

COPY src/ src/
COPY pyproject.toml .
COPY poetry.lock .

RUN poetry build


######################
# Production container
FROM python:3.8-slim

COPY --from=build /app/dist/*.whl /tmp/.

RUN pip install /tmp/*.whl

RUN rm /tmp/*.whl

CMD [ "gha", "--help" ]
