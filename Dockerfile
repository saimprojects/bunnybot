FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Ensure Python can find modules
ENV PYTHONPATH=/app

CMD ["python", "main.py"]