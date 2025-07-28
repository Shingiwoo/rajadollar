FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN adduser --disabled-password --gecos "" botuser
USER botuser

COPY --chown=botuser:botuser . .

EXPOSE 8588

CMD ["streamlit", "run", "main.py", "--server.port=8588", "--server.headless=true"]
