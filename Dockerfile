FROM python:3.12-slim

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir \
    streamlit \
    pandas \
    requests \
    python-binance==1.0.20 \
    scikit-learn \
    schedule \
    python-telegram-bot \
    python-dotenv \
    numpy \
    matplotlib \
    plotly \
    seaborn \
    nest_asyncio \
    statsmodels \
    yfinance \
    ta

RUN adduser --disabled-password --gecos "" botuser && \
    mkdir -p /app/logs && chown -R botuser /app/logs && \
    mkdir -p /app/runtime_state && chown -R botuser /app/runtime_state
USER botuser

EXPOSE 8588

CMD ["streamlit", "run", "main.py", "--server.port=8588", "--server.headless=true"]
