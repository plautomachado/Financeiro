# RM Money no Google Cloud Run (app próprio, fora do iframe -> login persiste).
FROM python:3.12-slim

WORKDIR /app

# OCR (ler texto de imagens/fotos de extrato) — tesseract + português
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr tesseract-ocr-por \
    && rm -rf /var/lib/apt/lists/*

# dependências primeiro (cache de build)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# código
COPY . .

# Cloud Run injeta a porta em $PORT (padrão 8080)
ENV PORT=8080
EXPOSE 8080

# Streamlit escutando na porta do Cloud Run
CMD streamlit run app.py \
    --server.port=${PORT} \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --server.enableCORS=false \
    --server.enableXsrfProtection=false
