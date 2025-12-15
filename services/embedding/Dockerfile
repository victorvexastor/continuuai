FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY services/embedding/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy service code
COPY services/embedding/app.py .

# Download model at build time (caching layer)
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

EXPOSE 8080
CMD ["python", "app.py"]
