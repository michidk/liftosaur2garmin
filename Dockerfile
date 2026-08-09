FROM python:3.12-slim

WORKDIR /app

RUN groupadd --system --gid 1000 app \
    && useradd --system --uid 1000 --gid app --create-home --home-dir /home/app app

COPY pyproject.toml README.md ./
COPY src/ src/

RUN pip install --no-cache-dir .

EXPOSE 8123

USER app

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; response = urllib.request.urlopen('http://localhost:8123/', timeout=3); response.close()"]

ENTRYPOINT ["liftosaur2garmin"]
CMD ["serve"]
