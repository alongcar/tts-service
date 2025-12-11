FROM python:3.12
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends \
    espeak-ng espeak-ng-data libespeak-ng1 libasound2 \
    && rm -rf /var/lib/apt/lists/* \
    && ln -s /usr/lib/x86_64-linux-gnu/libespeak-ng.so.1 /usr/lib/x86_64-linux-gnu/libespeak.so.1 || true \
    && ln -s /usr/lib/aarch64-linux-gnu/libespeak-ng.so.1 /usr/lib/aarch64-linux-gnu/libespeak.so.1 || true \
    && ln -s /usr/lib/libespeak-ng.so.1 /usr/lib/libespeak.so.1 || true
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN grep -v '^asyncio$' /app/requirements.txt > /app/requirements.clean.txt && \
    pip install --no-cache-dir -r /app/requirements.clean.txt
COPY . /app
EXPOSE 8765
CMD ["python", "app.py"]