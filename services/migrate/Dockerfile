FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir psycopg[binary]==3.2.1
COPY services/migrate/migrate_runner.py /app/migrate_runner.py
ENTRYPOINT ["python", "/app/migrate_runner.py"]
