FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir psycopg2-binary==2.9.10
COPY services/graph-deriver/app.py /app/app.py
CMD ["python", "/app/app.py"]
