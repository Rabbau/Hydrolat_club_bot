FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN pip config set global.index-url https://pypi.org/simple
RUN pip config set global.extra-index-url https://mirrors.yandex.ru/pypi/simple/

RUN set -eux; \
    apt_ok=0; \
    for i in 1 2 3 4 5; do \
      apt-get clean; \
      rm -rf /var/lib/apt/lists/*; \
      if apt-get update && apt-get install -y --no-install-recommends \
          ca-certificates \
          gcc \
          g++ \
          libpq-dev \
          postgresql-client \
          python3-dev; then \
        apt_ok=1; \
        break; \
      fi; \
      echo "apt install failed, retry $i/5"; \
      sleep 5; \
    done; \
    if [ "$apt_ok" -ne 1 ]; then \
      echo "apt install failed after retries"; \
      exit 1; \
    fi; \
    rm -rf /var/lib/apt/lists/*

# Копируем requirements.txt
COPY requirements.txt .

# # Устанавливаем Python зависимости
# RUN pip install --no-cache-dir --upgrade pip && \
#     pip install --no-cache-dir -r requirements.txt

RUN set -eux; \
    python -m pip install --no-cache-dir --upgrade pip; \
    pip_ok=0; \
    for i in 1 2 3 4 5; do \
      if python -m pip install --no-cache-dir --retries 10 --timeout 120 -r requirements.txt; then \
        pip_ok=1; \
        break; \
      fi; \
      echo "pip install failed, retry $i/5"; \
      sleep 5; \
    done; \
    if [ "$pip_ok" -ne 1 ]; then \
      echo "pip install failed after retries"; \
      exit 1; \
    fi; \
    python -m pip show alembic >/dev/null

# Копируем код
COPY . .

# Инициализируем Alembic (если нужно)
# RUN python init_alembic.py  

CMD ["python", "main.py"]
