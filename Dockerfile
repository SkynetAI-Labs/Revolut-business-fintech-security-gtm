FROM python:3.14.9-alpine@sha256:dbeb11d16bb95c3a7e3c25c842cb9f20cbc8c18f8be0461a4a0dcc861ad386a0

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN addgroup -g 10001 appuser \
    && adduser -D -H -u 10001 -G appuser -s /sbin/nologin appuser

COPY requirements.txt .
RUN python -m pip install --only-binary=:all: -r requirements.txt \
    && python -m pip check \
    && python -m pip uninstall -y pip \
    && python -c "import pathlib, shutil, sysconfig; shutil.rmtree(pathlib.Path(sysconfig.get_path('stdlib')) / 'ensurepip')"

COPY --chown=10001:10001 app/ ./app/
RUN mkdir -p /app/app/data \
    && chown 10001:10001 /app/app/data

USER 10001:10001

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
