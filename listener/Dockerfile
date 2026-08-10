# F1 Telemetry Listener
FROM python:3.12-slim

WORKDIR /app

COPY listener/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY listener/ .
COPY schema/ ./schema/

RUN mkdir -p /var/log/f1-listener

ENV PYTHONUNBUFFERED=1
ENV LISTEN_IP=0.0.0.0
ENV LISTEN_PORT=20777
ENV LOG_PATH=/var/log/f1-listener/listener.log

EXPOSE 20777/udp

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import os,sys; sys.exit(0 if any(b'main.py' in open(f'/proc/{p}/cmdline','rb').read() for p in os.listdir('/proc') if p.isdigit()) else 1)"

CMD ["python", "-u", "main.py"]
