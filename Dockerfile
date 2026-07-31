FROM mcr.microsoft.com/playwright/python:v1.52.0-noble

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONMALLOC=malloc
ENV MALLOC_ARENA_MAX=2

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends xvfb \
    && find /var/lib/apt/lists -mindepth 1 -delete

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

RUN mkdir -p /data/downloads /data/chrome-profile /data/state

# Chromium se ejecuta en modo visible dentro de una pantalla virtual. Esto
# conserva un comportamiento más próximo al navegador usado manualmente sin
# exponer una interfaz gráfica ni abrir puertos en la VM.
CMD ["xvfb-run", "-a", "-s", "-screen 0 1440x900x24", "python", "-m", "app.main"]
