FROM python:3.12-slim-bookworm

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    postgresql-client \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Копируем requirements.txt
COPY requirements.txt .

# # Устанавливаем Python зависимости
# RUN pip install --no-cache-dir --upgrade pip && \
#     pip install --no-cache-dir -r requirements.txt

RUN python -m pip install --no-cache-dir --upgrade pip && \
for i in 1 2 3 4 5; do \
    python -m pip install --no-cache-dir --retries 10 --timeout 120 -r requirements.txt && break || \
    (echo "pip install failed, retry $i/5"; sleep 5); \
done

# Копируем код
COPY . .

# Инициализируем Alembic (если нужно)
# RUN python init_alembic.py  

CMD ["python", "main.py"]