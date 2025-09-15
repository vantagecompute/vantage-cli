FROM 266735843730.dkr.ecr.us-west-2.amazonaws.com/notifications-api:1.0.0 as notifications-api
FROM 266735843730.dkr.ecr.us-west-2.amazonaws.com/sos-api:1.7.2 as sos-api
FROM 266735843730.dkr.ecr.us-west-2.amazonaws.com/jobbergate-api:5.6.0 as jobbergate-api
FROM 266735843730.dkr.ecr.us-west-2.amazonaws.com/lm-api:4.3.0 as lm-api

FROM python:3.10-slim-bookworm

WORKDIR /app
RUN mkdir scripts

RUN apt update && apt install -y curl libpq-dev gcc

RUN curl -sSL https://install.python-poetry.org | \
    POETRY_HOME=/opt/poetry POETRY_VERSION=1.5.1 python && \
    cd /usr/local/bin && \
    ln -s /opt/poetry/bin/poetry && \
    poetry config virtualenvs.create false

COPY ./pyproject.toml ./poetry.lock* /app/

RUN poetry install --no-root --no-dev

# copy Notifications API alembic folder
COPY --from=notifications-api /app/alembic ./scripts/notifications-api/alembic

# copy SOS API alembic folder
COPY --from=sos-api /app/alembic ./scripts/sos-api/alembic

# copy jobbergate api alembic folder
COPY --from=jobbergate-api /app/alembic ./scripts/jobbergate-api/alembic

# copy license manager api alembic folder
COPY --from=lm-api /app/alembic ./scripts/lm-api/alembic

# copy alembic folder
COPY ./alembic ./scripts/vantage-api/alembic
COPY ./alembic /app/alembic

COPY ./scripts /app/scripts/
COPY ./api /app/api

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "80"]
