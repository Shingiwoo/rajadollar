FROM python:3.13-alpine

WORKDIR /app

# Install dependencies first to leverage Docker cache
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    rm -rf /root/.cache/pip

# Copy the rest of the application
COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "main.py"]