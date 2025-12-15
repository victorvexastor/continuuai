FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi==0.115.5 uvicorn==0.32.1 psycopg[binary]==3.2.1 httpx==0.27.2
COPY services/retrieval/app.py /app/app.py
COPY services/retrieval/service.py /app/service.py
ENTRYPOINT ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
