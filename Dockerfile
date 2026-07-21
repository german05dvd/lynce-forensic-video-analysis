FROM python:3.11-slim

# ffmpeg: necesario para recortar los clips de video
# libgl1 / libglib2.0-0: dependencias runtime de opencv-python
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config.yaml .
COPY src/ ./src/

# Carpetas que se montarán como volúmenes en tiempo de ejecución
RUN mkdir -p /app/videos /app/output /app/models

ENTRYPOINT ["python", "-m", "src.cli"]
CMD ["--input", "/app/videos", "--output", "/app/output"]
