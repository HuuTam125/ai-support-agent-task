FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run once and exit (0 on success, 1 on failure) - no long-running server
CMD ["python", "main.py"]