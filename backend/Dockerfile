FROM python:3.11-slim

WORKDIR /app

# Install system deps for psycopg2 and PyMuPDF
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    libmupdf-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install CPU-only PyTorch first (150MB instead of 2.5GB CUDA packages)
RUN pip install --no-cache-dir torch==2.3.0 --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

# Create uploads directory
RUN mkdir -p uploads

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
