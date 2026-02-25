FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app

COPY requirements.txt .
RUN apt-get update -y && apt-get upgrade -y \
    && pip3 install -U pip \
    && pip3 install -U -r requirements.txt --no-cache-dir \
    # Clean up apt cache
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*


RUN playwright install chromium

COPY . .

CMD ["python3", "bot.py"]
