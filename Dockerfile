# ရိုးရိုး Python 3.11-slim ကို အသုံးပြုခြင်းဖြင့် Image Size ကို အများကြီး လျှော့ချနိုင်သည်
FROM python:3.11-slim-bullseye

# Python နှင့် System အတွက် လိုအပ်သော Environment Variables များ
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Yangon

WORKDIR /app

# Requirements ကို အရင် Copy ကူးခြင်းဖြင့် Docker Layer Cache ကို ပိုမိုမြန်ဆန်စေသည်
COPY requirements.txt .

# လိုအပ်သော Packages များနှင့် Playwright Chromium ကို (--with-deps ဖြင့်) တစ်ခါတည်း သွင်းသည်
RUN apt-get update -y \
    && apt-get install -y --no-install-recommends tzdata \
    && pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && playwright install chromium --with-deps \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ကျန်ရှိသော Bot Files များအားလုံးကို Copy ကူးသည်
COPY . .

# Bot ကို စတင် Run မည်
CMD ["python3", "pysa.py"]
