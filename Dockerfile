FROM python:3.12-slim

WORKDIR /app

COPY . /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

RUN adduser --disabled-password --gecos "" botuser && \
    mkdir -p /app/logs && chown -R botuser /app/logs && \
    mkdir -p /app/runtime_state && chown -R botuser /app/runtime_state
USER botuser
VOLUME ["/app/logs", "/app/runtime_state"]

EXPOSE 8588

CMD ["streamlit", "run", "main.py", "--server.port=8588", "--server.headless=true"]
