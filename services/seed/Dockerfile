FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir psycopg[binary]==3.2.1
COPY services/seed/seed.py /app/seed.py
ENTRYPOINT ["python", "/app/seed.py"]
