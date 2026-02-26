import io
import os
import re
import datetime
import time
from bs4 import BeautifulSoup
import random
from dotenv import load_dotenv
import asyncio
from playwright.async_api import async_playwright
import html
from collections import defaultdict

# 🟢 curl_cffi ကို Import လုပ်ခြင်း
from curl_cffi import requests as cffi_requests

# 🟢 Pyrofork (Pyrogram Namespace) Imports
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode

import database as db

# ==========================================
# 📌 ENVIRONMENT VARIABLES
# ==========================================
load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
API_ID = int(os.getenv('API_ID', 123456))  
API_HASH = os.getenv('API_HASH', "your_api_hash_here") 
OWNER_ID = int(os.getenv('OWNER_ID', 1318826936)) 
FB_EMAIL = os.getenv('FB_EMAIL')
FB_PASS = os.getenv('FB_PASS')

# 🐝 ScrapingBee API Key (ရှိလျှင်သုံးမည်၊ မရှိလျှင် ရိုးရိုး curl_cffi ကိုသာသုံးမည်)
SCRAPINGBEE_API_KEY = os.getenv('SCRAPINGBEE_API_KEY')

if not BOT_TOKEN:
    print("❌ Error: BOT_TOKEN is missing in the .env file.")
    exit()

MMT = datetime.timezone(datetime.timedelta(hours=6, minutes=30))

# 🟢 Initialize Pyrofork Client
app = Client(
    "smile_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# ==========================================
# 🚀 ADVANCED CONCURRENCY & LOCK SYSTEM
# ==========================================
user_locks = defaultdict(asyncio.Lock)
api_semaphore = asyncio.Semaphore(5) 
auth_lock = asyncio.Lock()  
last_login_time = 0         

# ==========================================
# 🐝 SCRAPINGBEE API WRAPPER CLASS
# ==========================================
class ScrapingBeeSession:
    """ScrapingBee API မှတစ်ဆင့် Request များကို ကြားခံပေးပို့မည့် Class"""
    def __init__(self, api_key, cookies):
        self.api_key = api_key
        self.cookies = cookies
        self.base_url = "https://app.scrapingbee.com/api/v1/"
        
    def _build_params(self, target_url, headers):
        # ScrapingBee သို့ ပို့မည့် Parameters များ
        params = {
            'api_key': self.api_key,
            'url': target_url,
            'forward_headers': 'true', 
            'render_js': 'false', # 🟢 API များကို ခေါ်ခြင်းဖြစ်၍ JS Render မလိုပါ (Credit သက်သာစေသည်)
        }
        # Cookie များကို ScrapingBee format သို့ ပြောင်းခြင်း
        if self.cookies:
            params['cookies'] = "; ".join([f"{k}={v}" for k, v in self.cookies.items()])
            
        # Headers များကို "Spb-" ခံ၍ ပေးပို့မှသာ ScrapingBee မှ Target သို့ ဆက်ပို့ပေးမည်
        spb_headers = {}
        if headers:
            for k, v in headers.items():
                spb_headers[f"Spb-{k}"] = str(v)
                
        return params, spb_headers

    def get(self, url, headers=None, **kwargs):
        params, spb_headers = self._build_params(url, headers)
        return cffi_requests.get(self.base_url, params=params, headers=spb_headers, impersonate="chrome120")

    def post(self, url, data=None, headers=None, **kwargs):
        params, spb_headers = self._build_params(url, headers)
        return cffi_requests.post(self.base_url, params=params, headers=spb_headers, data=data, impersonate="chrome120")

# ==========================================
# 🍪 MAIN SCRAPER (CURL_CFFI OR SCRAPINGBEE)
# ==========================================
async def get_main_scraper():
    raw_cookie = await db.get_main_cookie()
    cookie_dict = {}
    if raw_cookie:
        for item in raw_cookie.split(';'):
            if '=' in item:
                k, v = item.strip().split('=', 1)
                cookie_dict[k.strip()] = v.strip()
                
    # 🟢 .env တွင် SCRAPINGBEE_API_KEY ထည့်ထားပါက ScrapingBee ကို အသုံးပြုမည်
    if SCRAPINGBEE_API_KEY:
        return ScrapingBeeSession(SCRAPINGBEE_API_KEY, cookie_dict)
    
    # 🟢 မထည့်ထားပါက ရိုးရိုး curl_cffi ကိုသာ အသုံးပြုမည်
    scraper = cffi_requests.Session(impersonate="chrome120", cookies=cookie_dict)
    return scraper

# ==========================================
# 🤖 PLAYWRIGHT AUTO-LOGIN (FACEBOOK) [LOCKED & SAFE]
# ==========================================
async def auto_login_and_get_cookie():
    global last_login_time
    
    if not FB_EMAIL or not FB_PASS:
        print("❌ FB_EMAIL and FB_PASS are missing in .env.")
        return False
        
    # 🟢 သော့ခတ်ပါမည် (လူအများ ပြိုင်တူ Login ဝင်ခြင်းကို တားဆီးမည်)
    async with auth_lock:
        # 🟢 Double-Checked Locking (လွန်ခဲ့သော ၂ မိနစ်အတွင်း Login အောင်မြင်ထားလျှင် ထပ်မဝင်ပါ)
        if time.time() - last_login_time < 120:
            print("✅ ရှေ့ကလူ Cookie အသစ်ယူပေးသွားလို့ Login ထပ်ဝင်စရာမလိုတော့ပါ။")
            return True

        print("Logging in with Facebook to fetch new Cookie...")
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True, 
                    args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-blink-features=AutomationControlled']
                )
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={'width': 1280, 'height': 720}
                )
                page = await context.new_page()
                
                await page.goto("https://www.smile.one/customer/login")
                await asyncio.sleep(5) 
                
                async with context.expect_page() as popup_info:
                    await page.locator("a.login-btn-facebook, a[href*='facebook.com']").first.click()
                
                fb_popup = await popup_info.value
                await fb_popup.wait_for_load_state()
                
                await asyncio.sleep(2)
                await fb_popup.fill('input[name="email"]', FB_EMAIL)
                await asyncio.sleep(1)
                await fb_popup.fill('input[name="pass"]', FB_PASS)
                await asyncio.sleep(1)
                
                await fb_popup.click('button[name="login"], input[name="login"]')
                
                try:
                    await page.wait_for_url("**/customer/order**", timeout=30000)
                    print("✅ Auto-Login successful. Saving Cookie...")
                    
                    cookies = await context.cookies()
                    cookie_dict = {cookie['name']: cookie['value'] for cookie in cookies}
                    raw_cookie_str = "; ".join([f"{k}={v}" for k, v in cookie_dict.items()])
                    
                    await db.update_main_cookie(raw_cookie_str)
                    await browser.close()
                    
                    # 🟢 အောင်မြင်သွားလျှင် နောက်ဆုံး Login ဝင်ခဲ့သည့် အချိန်ကို မှတ်ထားပါမည်
                    last_login_time = time.time()
                    return True
                    
                except Exception as wait_e:
                    print(f"❌ Did not reach the Order page. (Possible Facebook Checkpoint): {wait_e}")
                    await browser.close()
                    return False
                
        except Exception as e:
            print(f"❌ Error during Auto-Login: {e}")
            return False

# ==========================================
# 📌 PACKAGES
# ==========================================
DOUBLE_DIAMOND_PACKAGES = {
    '55': [{'pid': '22590', 'price': 39.0, 'name': '50+50 💎'}],
    '165': [{'pid': '22591', 'price': 116.9, 'name': '150+150 💎'}],
    '275': [{'pid': '22592', 'price': 187.5, 'name': '250+250 💎'}],
    '565': [{'pid': '22593', 'price': 385, 'name': '500+500 💎'}],
}

BR_PACKAGES = {
    '86': [{'pid': '13', 'price': 61.5, 'name': '86 💎'}],
    '172': [{'pid': '23', 'price': 122.0, 'name': '172 💎'}],
    '257': [{'pid': '25', 'price': 177.5, 'name': '257 💎'}],
    '343': [{'pid': '13', 'price': 61.5, 'name': '86 💎'}, {'pid': '25', 'price': 177.5, 'name': '257 💎'}],
    '429': [{'pid': '23', 'price': 122.0, 'name': '86 💎'}, {'pid': '25', 'price': 177.5, 'name': '257 💎'}],
    '514': [{'pid': '25', 'price': 177.5, 'name': '257 💎'}, {'pid': '25', 'price': 177.5, 'name': '257 💎'}],
    '600': [{'pid': '13', 'price': 61.5, 'name': '86 💎'}, {'pid': '25', 'price': 177.5, 'name': '257 💎'}, {'pid': '25', 'price': 177.5, 'name': '257 💎'}],
    '706': [{'pid': '26', 'price': 480.0, 'name': '706 💎'}],
    '878': [{'pid': '23', 'price': 122.0, 'name': '172 💎'}, {'pid': '26', 'price': 480.0, 'name': '706 💎'}],
    '963': [{'pid': '25', 'price': 177.5, 'name': '257 💎'}, {'pid': '26', 'price': 480.0, 'name': '706 💎'}],
    '1049': [{'pid': '13', 'price': 61.5, 'name': '86 💎'}, {'pid': '25', 'price': 177.5, 'name': '257 💎'}, {'pid': '26', 'price': 480.0, 'name': '706 💎'}],
    '1135': [{'pid': '23', 'price': 122.0, 'name': '172 💎'}, {'pid': '25', 'price': 177.5, 'name': '257 💎'}, {'pid': '26', 'price': 480.0, 'name': '706 💎'}],
    '1412': [{'pid': '26', 'price': 480.0, 'name': '706 💎'}, {'pid': '26', 'price': 480.0, 'name': '706 💎'}],
    '1584': [{'pid': '23', 'price': 122.0, 'name': '172 💎'}, {'pid': '26', 'price': 480.0, 'name': '706 💎'}, {'pid': '26', 'price': 480.0, 'name': '706 💎'}],
    '1755': [{'pid': '13', 'price': 61.5, 'name': '86 💎'}, {'pid': '25', 'price': 177.5, 'name': '257 💎'}, {'pid': '26', 'price': 480.0, 'name': '706 💎'}, {'pid': '26', 'price': 480.0, 'name': '706 💎'}],
    '2195': [{'pid': '27', 'price': 1453.0, 'name': '2195 💎'}],
    '2538': [{'pid': '13', 'price': 61.5, 'name': '86 💎'}, {'pid': '25', 'price': 177.5, 'name': '257 💎'}, {'pid': '27', 'price': 1453.0, 'name': '2195 💎'}],
    '2901': [{'pid': '27', 'price': 1453.0, 'name': '2195 💎'}, {'pid': '26', 'price': 480.0, 'name': '706 💎'}],
    '3244': [{'pid': '13', 'price': 61.5, 'name': '86 💎'}, {'pid': '25', 'price': 177.5, 'name': '257 💎'}, {'pid': '26', 'price': 480.0, 'name': '706 💎'}, {'pid': '27', 'price': 1453.0, 'name': '2195 💎'}],
    '3688': [{'pid': '28', 'price': 2424.0, 'name': '3688 💎'}],
    '5532': [{'pid': '29', 'price': 3660.0, 'name': '5532 💎'}],
    '9288': [{'pid': '30', 'price': 6079.0, 'name': '9288 💎'}],
    'meb': [{'pid': '26556', 'price': 196.5, 'name': 'Epic Monthly Package'}],
    'tp': [{'pid': '33', 'price': 402.5, 'name': 'Twilight Passage'}],
    'web': [{'pid': '26555', 'price': 39.0, 'name': 'Elite Weekly Paackage'}],
    'wp': [{'pid': '16642', 'price': 76.0, 'name': 'Weekly Pass'}],
}

PH_PACKAGES = {
    '11': [{'pid': '212', 'price': 9.50, 'name': '11 💎'}],
    '22': [{'pid': '213', 'price': 19.0, 'name': '22 💎'}],
    '56': [{'pid': '214', 'price': 47.50, 'name': '56 💎'}],
    '112': [{'pid': '214', 'price': 47.50, 'name': '56 💎'}, {'pid': '214', 'price': 47.50, 'name': '56 💎'}],
    'pwp': [{'pid': '16641', 'price': 95.00, 'name': 'Weekly Pass'}],
}

MCC_PACKAGES = {
    '86': [{'pid': '23825', 'price': 62.5, 'name': '86 💎'}],
    '172': [{'pid': '23826', 'price': 125.0, 'name': '172 💎'}],
    '257': [{'pid': '23827', 'price': 187.0, 'name': '257 💎'}],
    '343': [{'pid': '23828', 'price': 250.0, 'name': '343 💎'}],
    '429': [{'pid': '23826', 'price': 122.0, 'name': '172 💎'}, {'pid': '23827', 'price': 187.0, 'name': '257 💎'}],
    '516': [{'pid': '23829', 'price': 375.0, 'name': '516 💎'}],
    '600': [{'pid': '23825', 'price': 62.5, 'name': '86 💎'}, {'pid': '23827', 'price': 187.0, 'name': '257 💎'}, {'pid': '23827', 'price': 177.5, 'name': '257 💎'}],
    '706': [{'pid': '23830', 'price': 500.0, 'name': '706 💎'}],
    '878': [{'pid': '23826', 'price': 125.0, 'name': '172 💎'}, {'pid': '23830', 'price': 500.0, 'name': '706 💎'}],
    '963': [{'pid': '23827', 'price': 187.0, 'name': '257 💎'}, {'pid': '23830', 'price': 500.0, 'name': '706 💎'}],
    '1049': [{'pid': '23825', 'price': 62.5, 'name': '86 💎'}, {'pid': '23827', 'price': 187.0, 'name': '257 💎'}, {'pid': '23830', 'price': 500.0, 'name': '706 💎'}],
    '1135': [{'pid': '23826', 'price': 125.0, 'name': '172 💎'}, {'pid': '23827', 'price': 187.0, 'name': '257 💎'}, {'pid': '23830', 'price': 500.0, 'name': '706 💎'}],
    '1346': [{'pid': '23831', 'price': 937.5, 'name': '1346 💎'}],
    '1412': [{'pid': '23830', 'price': 500.0, 'name': '706 💎'}, {'pid': '23830', 'price': 500.0, 'name': '706 💎'}],
    '1584': [{'pid': '23826', 'price': 125.0, 'name': '172 💎'}, {'pid': '23830', 'price': 500.0, 'name': '706 💎'}, {'pid': '23830', 'price': 480.0, 'name': '706 💎'}],
    '1755': [{'pid': '23825', 'price': 62.5, 'name': '86 💎'}, {'pid': '23827', 'price': 187.0, 'name': '257 💎'}, {'pid': '23830', 'price': 500.0, 'name': '706 💎'}, {'pid': '23830', 'price': 500.0, 'name': '706 💎'}],
    '1825': [{'pid': '23832', 'price': 1250.0, 'name': '1825 💎'}],
    '2195': [{'pid': '23833', 'price': 1500.0, 'name': '2195 💎'}],
    '2538': [{'pid': '23825', 'price': 62.5, 'name': '86 💎'}, {'pid': '23827', 'price': 187.0, 'name': '257 💎'}, {'pid': '23833', 'price': 1500.0, 'name': '2195 💎'}],
    '2901': [{'pid': '23833', 'price': 1500.0, 'name': '2195 💎'}, {'pid': '23830', 'price': 500.0, 'name': '706 💎'}],
    '3244': [{'pid': '23825', 'price': 62.5, 'name': '86 💎'}, {'pid': '23827', 'price': 187.0, 'name': '257 💎'}, {'pid': '23830', 'price': 500.0, 'name': '706 💎'}, {'pid': '23833', 'price': 1500.0, 'name': '2195 💎'}],
    '3688': [{'pid': '23834', 'price': 2500.0, 'name': '3688 💎'}],
    '5532': [{'pid': '23835', 'price': 3750.0, 'name': '5532 💎'}],
    '9288': [{'pid': '23836', 'price': 6250.0, 'name': '9288 💎'}],
    'b150': [{'pid': '23838', 'price': 120.0, 'name': '150+150 💎'}],
    'b250': [{'pid': '23839', 'price': 200.0, 'name': '250+250 💎'}],
    'b50': [{'pid': '23837', 'price': 40.0, 'name': '50+50 💎'}],
    'b500': [{'pid': '23840', 'price': 400, 'name': '500+500 💎'}],
    'wp': [{'pid': '23841', 'price': 76.0, 'name': 'Weekly Pass'}],
}

PH_MCC_PACKAGES = {
    '5': [{'pid': '23906', 'price': 4.75, 'name': '5 💎'}],
}

# ==========================================
# 2. FUNCTION TO GET REAL BALANCE
# ==========================================
async def get_smile_balance(scraper, headers, balance_url='https://www.smile.one/customer/order'):
    balances = {'br_balance': 0.00, 'ph_balance': 0.00}
    try:
        response = await asyncio.to_thread(scraper.get, balance_url, headers=headers, timeout=15)
        
        br_match = re.search(r'(?i)(?:Balance|Saldo)[\s:]*?<\/p>\s*<p>\s*([\d\.,]+)', response.text)
        if br_match: balances['br_balance'] = float(br_match.group(1).replace(',', ''))
        else:
            soup = BeautifulSoup(response.text, 'html.parser')
            main_balance_div = soup.find('div', class_='balance-coins')
            if main_balance_div:
                p_tags = main_balance_div.find_all('p')
                if len(p_tags) >= 2: balances['br_balance'] = float(p_tags[1].text.strip().replace(',', ''))
                    
        ph_match = re.search(r'(?i)Saldo PH[\s:]*?<\/span>\s*<span>\s*([\d\.,]+)', response.text)
        if ph_match: balances['ph_balance'] = float(ph_match.group(1).replace(',', ''))
        else:
            soup = BeautifulSoup(response.text, 'html.parser')
            ph_balance_container = soup.find('div', id='all-balance')
            if ph_balance_container:
                span_tags = ph_balance_container.find_all('span')
                if len(span_tags) >= 2: balances['ph_balance'] = float(span_tags[1].text.strip().replace(',', ''))
    except Exception as e: 
        print(f"Error fetching balance from site: {e}")
    return balances

# ==========================================
# 3. SMILE.ONE SCRAPER FUNCTION (MLBB)
# ==========================================
async def process_smile_one_order(game_id, zone_id, product_id, currency_name, prev_context=None):
    scraper = await get_main_scraper()

    if currency_name == 'PH':
        main_url = 'https://www.smile.one/ph/merchant/mobilelegends'
        checkrole_url = 'https://www.smile.one/ph/merchant/mobilelegends/checkrole'
        query_url = 'https://www.smile.one/ph/merchant/mobilelegends/query'
        pay_url = 'https://www.smile.one/ph/merchant/mobilelegends/pay'
        order_api_url = 'https://www.smile.one/ph/customer/activationcode/codelist'
    else:
        main_url = 'https://www.smile.one/merchant/mobilelegends'
        checkrole_url = 'https://www.smile.one/merchant/mobilelegends/checkrole'
        query_url = 'https://www.smile.one/merchant/mobilelegends/query'
        pay_url = 'https://www.smile.one/merchant/mobilelegends/pay'
        order_api_url = 'https://www.smile.one/customer/activationcode/codelist'
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest', 
        'Referer': main_url, 
        'Origin': 'https://www.smile.one'
    }

    try:
        csrf_token = None
        ig_name = "Unknown"
        
        # 🟢 Context ရှိနေပါက Token နှင့် Name ကို ပြန်လည်အသုံးပြုမည် (အလွန်မြန်ဆန်သွားမည်)
        if prev_context:
            csrf_token = prev_context.get('csrf_token')
            ig_name = prev_context.get('ig_name')

        # 🟢 Context မရှိပါက (ပထမဆုံးပစ္စည်းအတွက်) Token အသစ်တောင်းမည်
        if not csrf_token:
            response = await asyncio.to_thread(scraper.get, main_url, headers=headers)
            if response.status_code in [403, 503] or "cloudflare" in response.text.lower():
                 return {"status": "error", "message": "Blocked by Cloudflare."}

            soup = BeautifulSoup(response.text, 'html.parser')
            meta_tag = soup.find('meta', {'name': 'csrf-token'})
            if meta_tag: csrf_token = meta_tag.get('content')
            else:
                csrf_input = soup.find('input', {'name': '_csrf'})
                if csrf_input: csrf_token = csrf_input.get('value')

            if not csrf_token: return {"status": "error", "message": "CSRF Token not found. Add a new Cookie using /setcookie."}

        # 🟢 Context မရှိပါက (ပထမဆုံးပစ္စည်းအတွက်) Game ID စစ်ဆေးမည်
        if not prev_context:
            check_data = {'user_id': game_id, 'zone_id': zone_id, '_csrf': csrf_token}
            role_response_raw = await asyncio.to_thread(scraper.post, checkrole_url, data=check_data, headers=headers)
            try:
                role_result = role_response_raw.json()
                ig_name = role_result.get('username') or role_result.get('data', {}).get('username')
                if not ig_name or str(ig_name).strip() == "":
                    real_error = role_result.get('msg') or role_result.get('message') or "Account not found."
                    return {"status": "error", "message": f"❌ Invalid Account: {real_error}"}
            except Exception: return {"status": "error", "message": "Check Role API Error: Cannot verify account."}

        # Query & Pay အပိုင်း (ပုံမှန်အတိုင်း အလုပ်လုပ်မည်)
        query_data = {'user_id': game_id, 'zone_id': zone_id, 'pid': product_id, 'checkrole': '', 'pay_methond': 'smilecoin', 'channel_method': 'smilecoin', '_csrf': csrf_token}
        query_response_raw = await asyncio.to_thread(scraper.post, query_url, data=query_data, headers=headers)
        
        try: query_result = query_response_raw.json()
        except Exception: return {"status": "error", "message": "Query API Error"}
            
        flowid = query_result.get('flowid') or query_result.get('data', {}).get('flowid')
        
        if not flowid:
            real_error = query_result.get('msg') or query_result.get('message') or ""
            if "login" in str(real_error).lower() or "unauthorized" in str(real_error).lower():
                print("⚠️ Cookie expired. Starting Auto-Login...")
                
                # 🟢 အသစ်ရေးထားသော Function ဖြင့် Owner ဆီ စာပို့မည်
                await notify_owner("⚠️ <b>Order Alert:</b> Cookie သက်တမ်းကုန်သွားပါပြီ။ အော်ဒါဝယ်နေစဉ် Auto-login စတင်နေပါသည်...")

                success = await auto_login_and_get_cookie()
                
                if success:
                    await notify_owner("✅ <b>Success:</b> Auto-login အောင်မြင်ပါသည်။ Cookie အသစ်ရရှိပါပြီ။")
                    return {"status": "error", "message": "Session renewed. Please enter the command again."}
                else: 
                    await notify_owner("❌ <b>Critical Alert:</b> Auto-login ဝင်ရောက်ခြင်း မအောင်မြင်ပါ။ `/setcookie` ဖြင့် Manual ပြန်ထည့်ပေးပါ။")
                    return {"status": "error", "message": "❌ Auto-Login failed. Please provide /setcookie again."}
            return {"status": "error", "message": "❌ **Invalid Account:**\nAccount is ban server."}

        last_known_order_id = None
        try:
            pre_hist_raw = await asyncio.to_thread(scraper.get, order_api_url, params={'type': 'orderlist', 'p': '1', 'pageSize': '5'}, headers=headers)
            pre_hist_json = pre_hist_raw.json()
            if 'list' in pre_hist_json and len(pre_hist_json['list']) > 0:
                for order in pre_hist_json['list']:
                    if str(order.get('user_id')) == str(game_id) and str(order.get('server_id')) == str(zone_id):
                        last_known_order_id = str(order.get('increment_id', ""))
                        break
        except Exception: pass

        pay_data = {'_csrf': csrf_token, 'user_id': game_id, 'zone_id': zone_id, 'pay_methond': 'smilecoin', 'product_id': product_id, 'channel_method': 'smilecoin', 'flowid': flowid, 'email': '', 'coupon_id': ''}
        pay_response_raw = await asyncio.to_thread(scraper.post, pay_url, data=pay_data, headers=headers)
        pay_text = pay_response_raw.text.lower()
        
        if "saldo insuficiente" in pay_text or "insufficient" in pay_text:
            return {"status": "error", "message": "Insufficient balance in the Main account."}
        
        await asyncio.sleep(2) 
        real_order_id = "Not found"
        is_success = False

        try:
            hist_res_raw = await asyncio.to_thread(scraper.get, order_api_url, params={'type': 'orderlist', 'p': '1', 'pageSize': '5'}, headers=headers)
            hist_json = hist_res_raw.json()
            if 'list' in hist_json and len(hist_json['list']) > 0:
                for order in hist_json['list']:
                    if str(order.get('user_id')) == str(game_id) and str(order.get('server_id')) == str(zone_id):
                        current_order_id = str(order.get('increment_id', ""))
                        if current_order_id != last_known_order_id:
                            if str(order.get('order_status', '')).lower() == 'success' or str(order.get('status')) == '1':
                                real_order_id = current_order_id
                                is_success = True
                                break
        except Exception: pass

        if not is_success:
            try:
                pay_json = pay_response_raw.json()
                code = str(pay_json.get('code', ''))
                msg = str(pay_json.get('msg', '')).lower()
                if code in ['200', '0', '1'] or 'success' in msg: is_success = True
            except:
                if 'success' in pay_text or 'sucesso' in pay_text: is_success = True

        if is_success:
            # 🟢 csrf_token ပါ ထည့်ပြန်ပေးလိုက်ပါမည်
            return {"status": "success", "ig_name": ig_name, "order_id": real_order_id, "csrf_token": csrf_token}
        else:
            err_msg = "Payment failed."
            try:
                err_json = pay_response_raw.json()
                if 'msg' in err_json: err_msg = f"Payment failed. ({err_json['msg']})"
            except: pass
            return {"status": "error", "message": err_msg}

    except Exception as e: return {"status": "error", "message": f"System Error: {str(e)}"}

# 🌟 3.1 MAGIC CHESS SCRAPER FUNCTION
async def process_mcc_order(game_id, zone_id, product_id, currency_name, prev_context=None):
    scraper = await get_main_scraper()

    if currency_name == 'PH':
        main_url = 'https://www.smile.one/ph/merchant/game/magicchessgogo'
        checkrole_url = 'https://www.smile.one/ph/merchant/game/checkrole'
        query_url = 'https://www.smile.one/ph/merchant/game/query'
        pay_url = 'https://www.smile.one/ph/merchant/game/pay'
        order_api_url = 'https://www.smile.one/ph/customer/activationcode/codelist'
    else:
        main_url = 'https://www.smile.one/merchant/game/magicchessgogo'
        checkrole_url = 'https://www.smile.one/merchant/game/checkrole'
        query_url = 'https://www.smile.one/merchant/game/query'
        pay_url = 'https://www.smile.one/merchant/game/pay'
        order_api_url = 'https://www.smile.one/customer/activationcode/codelist'
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest', 
        'Referer': main_url, 
        'Origin': 'https://www.smile.one'
    }

    try:
        csrf_token = None
        ig_name = "Unknown"
        
        # 🟢 Context ရှိနေပါက Token နှင့် Name ကို ပြန်လည်အသုံးပြုမည်
        if prev_context:
            csrf_token = prev_context.get('csrf_token')
            ig_name = prev_context.get('ig_name')

        if not csrf_token:
            response = await asyncio.to_thread(scraper.get, main_url, headers=headers)
            if response.status_code in [403, 503] or "cloudflare" in response.text.lower():
                 return {"status": "error", "message": "Blocked by Cloudflare."}

            soup = BeautifulSoup(response.text, 'html.parser')
            meta_tag = soup.find('meta', {'name': 'csrf-token'})
            if meta_tag: csrf_token = meta_tag.get('content')
            else:
                csrf_input = soup.find('input', {'name': '_csrf'})
                if csrf_input: csrf_token = csrf_input.get('value')

            if not csrf_token: return {"status": "error", "message": "CSRF Token not found. Add a new Cookie using /setcookie."}

        if not prev_context:
            check_data = {'user_id': game_id, 'zone_id': zone_id, '_csrf': csrf_token}
            role_response_raw = await asyncio.to_thread(scraper.post, checkrole_url, data=check_data, headers=headers)
            try:
                role_result = role_response_raw.json()
                ig_name = role_result.get('username') or role_result.get('data', {}).get('username')
                if not ig_name or str(ig_name).strip() == "":
                    return {"status": "error", "message": " Account not found."}
            except Exception: return {"status": "error", "message": "⚠️ Check Role API Error: Cannot verify account."}

        query_data = {'user_id': game_id, 'zone_id': zone_id, 'pid': product_id, 'checkrole': '', 'pay_methond': 'smilecoin', 'channel_method': 'smilecoin', '_csrf': csrf_token}
        query_response_raw = await asyncio.to_thread(scraper.post, query_url, data=query_data, headers=headers)
        
        try: query_result = query_response_raw.json()
        except Exception: return {"status": "error", "message": "Query API Error"}
            
        flowid = query_result.get('flowid') or query_result.get('data', {}).get('flowid')
        
        if not flowid:
            real_error = query_result.get('msg') or query_result.get('message') or ""
            if "login" in str(real_error).lower() or "unauthorized" in str(real_error).lower():
                print("⚠️ Cookie expired. Starting Auto-Login...")
                
                # 🟢 အသစ်ရေးထားသော Function ဖြင့် Owner ဆီ စာပို့မည်
                await notify_owner("⚠️ <b>Order Alert:</b> Cookie သက်တမ်းကုန်သွားပါပြီ။ အော်ဒါဝယ်နေစဉ် Auto-login စတင်နေပါသည်...")

                success = await auto_login_and_get_cookie()
                
                if success:
                    await notify_owner("✅ <b>Success:</b> Auto-login အောင်မြင်ပါသည်။ Cookie အသစ်ရရှိပါပြီ။")
                    return {"status": "error", "message": "Session renewed. Please enter the command again."}
                else: 
                    await notify_owner("❌ <b>Critical Alert:</b> Auto-login ဝင်ရောက်ခြင်း မအောင်မြင်ပါ။ `/setcookie` ဖြင့် Manual ပြန်ထည့်ပေးပါ။")
                    return {"status": "error", "message": "❌ Auto-Login failed. Please provide /setcookie again."}
            return {"status": "error", "message": "Invalid account or unable to purchase."}

        last_known_order_id = None
        try:
            pre_hist_raw = await asyncio.to_thread(scraper.get, order_api_url, params={'type': 'orderlist', 'p': '1', 'pageSize': '5'}, headers=headers)
            pre_hist_json = pre_hist_raw.json()
            if 'list' in pre_hist_json and len(pre_hist_json['list']) > 0:
                for order in pre_hist_json['list']:
                    if str(order.get('user_id')) == str(game_id) and str(order.get('server_id')) == str(zone_id):
                        last_known_order_id = str(order.get('increment_id', ""))
                        break
        except Exception: pass

        pay_data = {'_csrf': csrf_token, 'user_id': game_id, 'zone_id': zone_id, 'pay_methond': 'smilecoin', 'product_id': product_id, 'channel_method': 'smilecoin', 'flowid': flowid, 'email': '', 'coupon_id': ''}
        pay_response_raw = await asyncio.to_thread(scraper.post, pay_url, data=pay_data, headers=headers)
        pay_text = pay_response_raw.text.lower()
        
        if "saldo insuficiente" in pay_text or "insufficient" in pay_text:
            return {"status": "error", "message": "Insufficient balance in the Main account."}
        
        await asyncio.sleep(2) 
        real_order_id = "Not found"
        is_success = False

        try:
            hist_res_raw = await asyncio.to_thread(scraper.get, order_api_url, params={'type': 'orderlist', 'p': '1', 'pageSize': '5'}, headers=headers)
            hist_json = hist_res_raw.json()
            if 'list' in hist_json and len(hist_json['list']) > 0:
                for order in hist_json['list']:
                    if str(order.get('user_id')) == str(game_id) and str(order.get('server_id')) == str(zone_id):
                        current_order_id = str(order.get('increment_id', ""))
                        if current_order_id != last_known_order_id:
                            if str(order.get('order_status', '')).lower() == 'success' or str(order.get('status')) == '1':
                                real_order_id = current_order_id
                                is_success = True
                                break
        except Exception: pass

        if not is_success:
            try:
                pay_json = pay_response_raw.json()
                code = str(pay_json.get('code', ''))
                msg = str(pay_json.get('msg', '')).lower()
                if code in ['200', '0', '1'] or 'success' in msg: is_success = True
            except:
                if 'success' in pay_text or 'sucesso' in pay_text: is_success = True

        if is_success:
            # 🟢 csrf_token ပါ ထည့်ပြန်ပေးလိုက်ပါမည်
            return {"status": "success", "ig_name": ig_name, "order_id": real_order_id, "csrf_token": csrf_token}
        else:
            err_msg = "Payment failed."
            try:
                err_json = pay_response_raw.json()
                if 'msg' in err_json: err_msg = f"Payment failed. ({err_json['msg']})"
            except: pass
            return {"status": "error", "message": err_msg}

    except Exception as e: return {"status": "error", "message": f"System Error: {str(e)}"}

# ==========================================
# 4. 🛡️ FUNCTION TO CHECK AUTHORIZATION
# ==========================================
async def is_authorized(message: Message):
    if message.from_user.id == OWNER_ID:
        return True
    user = await db.get_reseller(message.from_user.id)
    return user is not None

# ==========================================
# 5. RESELLER MANAGEMENT & COMMANDS
# ==========================================
@app.on_message(filters.command("add"))
async def add_reseller(client, message: Message):
    if message.from_user.id != OWNER_ID: return await message.reply("You are not the Owner.")
    parts = message.text.split()
    if len(parts) < 2: return await message.reply("`/add <user_id>`")
        
    target_id = parts[1].strip()
    if not target_id.isdigit(): return await message.reply("Please enter the User ID in numbers only.")
        
    if await db.add_reseller(target_id, f"User_{target_id}"):
        await message.reply(f"✅ Reseller ID `{target_id}` has been approved.")
    else:
        await message.reply(f"Reseller ID `{target_id}` is already in the list.")

@app.on_message(filters.command("remove"))
async def remove_reseller(client, message: Message):
    if message.from_user.id != OWNER_ID: return await message.reply("You are not the Owner.")
    parts = message.text.split()
    if len(parts) < 2: return await message.reply("Usage format - `/remove <user_id>`")
        
    target_id = parts[1].strip()
    if target_id == str(OWNER_ID): return await message.reply("The Owner cannot be removed.")
        
    if await db.remove_reseller(target_id):
        await message.reply(f"✅ Reseller ID `{target_id}` has been removed.")
    else:
        await message.reply("That ID is not in the list.")

@app.on_message(filters.command("users"))
async def list_resellers(client, message: Message):
    if message.from_user.id != OWNER_ID: return await message.reply("You are not the Owner.")
    resellers_list = await db.get_all_resellers()
    user_list = []
    
    for r in resellers_list:
        role = "owner" if r["tg_id"] == str(OWNER_ID) else "users"
        user_list.append(f"🟢 ID: `{r['tg_id']}` ({role})\n   BR: ${r.get('br_balance', 0.0)} | PH: ${r.get('ph_balance', 0.0)}")
            
    final_text = "\n\n".join(user_list) if user_list else "No users found."
    await message.reply(f"🟢 **Approved users List (V-Wallet):**\n\n{final_text}")

@app.on_message(filters.command("setcookie"))
async def set_cookie_command(client, message: Message):
    if message.from_user.id != OWNER_ID: return await message.reply("❌ Only the Owner can set the Cookie.")
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2: return await message.reply("⚠️ **Usage format:**\n`/setcookie <Long_Main_Cookie>`")
    
    await db.update_main_cookie(parts[1].strip())
    await message.reply("✅ **Main Cookie has been successfully updated securely.**")

@app.on_message(filters.regex("PHPSESSID") & filters.regex("cf_clearance"))
async def handle_raw_cookie_dump(client, message: Message):
    if message.from_user.id != OWNER_ID: 
        return await message.reply("❌ You are not the owner.")

    text = message.text
    try:
        phpsessid_match = re.search(r"['\"]?PHPSESSID['\"]?\s*[:=]\s*['\"]?([^'\";\s]+)['\"]?", text)
        cf_clearance_match = re.search(r"['\"]?cf_clearance['\"]?\s*[:=]\s*['\"]?([^'\";\s]+)['\"]?", text)
        cf_bm_match = re.search(r"['\"]?__cf_bm['\"]?\s*[:=]\s*['\"]?([^'\";\s]+)['\"]?", text)
        did_match = re.search(r"['\"]?_did['\"]?\s*[:=]\s*['\"]?([^'\";\s]+)['\"]?", text)

        if not phpsessid_match or not cf_clearance_match:
            return await message.reply("PHPSESSID နှင့် cf_clearance ကို ရှာမတွေ့ပါ။ Format မှန်ကန်ကြောင်း စစ်ဆေးပါ။")

        val_php = phpsessid_match.group(1)
        val_cf = cf_clearance_match.group(1)

        formatted_cookie = f"PHPSESSID={val_php}; cf_clearance={val_cf};"
        
        if cf_bm_match: formatted_cookie += f" __cf_bm={cf_bm_match.group(1)};"
        if did_match: formatted_cookie += f" _did={did_match.group(1)};"

        await db.update_main_cookie(formatted_cookie)
        await message.reply(f"✅ **Smart Cookie Parser: Success!**\n\n🍪 **Saved Cookie:**\n`{formatted_cookie}`")
    except Exception as e:
        await message.reply(f"❌ Parsing Error: {str(e)}")

# ==========================================
# 💳 BALANCE COMMAND & TOOLS
# ==========================================
@app.on_message(filters.command("balance"))
async def check_balance_command(client, message: Message):
    if not await is_authorized(message): return await message.reply("ɴᴏᴛ ᴀᴜᴛʜᴏʀɪᴢᴇᴅ ᴜsᴇʀ.")
    
    tg_id = str(message.from_user.id)
    user_wallet = await db.get_reseller(tg_id)
    if not user_wallet: return await message.reply("Yᴏᴜʀ ᴀᴄᴄᴏᴜɴᴛ ɪɴғᴏʀᴍᴀᴛɪᴏɴ ᴄᴀɴɴᴏᴛ ʙᴇ ғᴏᴜɴᴅ.")
    
    ICON_EMOJI = "5956330306167376831"
    BR_EMOJI = "5228878788867142213"
    PH_EMOJI = "5231361434583049965"

    report = (
        f"<blockquote><emoji id='{ICON_EMOJI}'>💳</emoji> <b>YOUR WALLET BALANCE</b>\n\n"
        f"<emoji id='{BR_EMOJI}'>🇧🇷</emoji> BR BALANCE : ${user_wallet.get('br_balance', 0.0):,.2f}\n"
        f"<emoji id='{PH_EMOJI}'>🇵🇭</emoji> PH BALANCE : ${user_wallet.get('ph_balance', 0.0):,.2f}</blockquote>"
    )
    
    if message.from_user.id == OWNER_ID:
        loading_msg = await message.reply("Fetching real balance from the official account...")
        scraper = await get_main_scraper()
        headers = {'X-Requested-With': 'XMLHttpRequest', 'Origin': 'https://www.smile.one'}
        try:
            balances = await get_smile_balance(scraper, headers, 'https://www.smile.one/customer/order')
            report += (
                f"\n\n<blockquote><emoji id='{ICON_EMOJI}'>💳</emoji> <b>OFFICIAL ACCOUNT BALANCE</b>\n\n"
                f"<emoji id='{BR_EMOJI}'>🇧🇷</emoji> BR BALANCE : ${balances.get('br_balance', 0.00):,.2f}\n"
                f"<emoji id='{PH_EMOJI}'>🇵🇭</emoji> PH BALANCE : ${balances.get('ph_balance', 0.00):,.2f}</blockquote>"
            )
            await loading_msg.edit_text(report, parse_mode=ParseMode.HTML)
        except Exception as e:
            print(f"Balance Command Error: {e}")
            try:
                await loading_msg.edit_text(report, parse_mode=ParseMode.HTML)
            except Exception as parse_error:
                await loading_msg.edit_text(f"❌ View Error: {parse_error}\nYour V-Wallet Balance is BR: ${user_wallet.get('br_balance', 0.0):,.2f} | PH: ${user_wallet.get('ph_balance', 0.0):,.2f}")
    else:
        await message.reply(report, parse_mode=ParseMode.HTML)

@app.on_message(filters.command("history") | filters.regex(r"(?i)^\.his$"))
async def send_order_history(client, message: Message):
    if not await is_authorized(message): return await message.reply("ɴᴏᴛ ᴀᴜᴛʜᴏʀɪᴢᴇᴅ ᴜsᴇʀ.")
    tg_id = str(message.from_user.id)
    user_name = message.from_user.username or message.from_user.first_name
    
    history_data = await db.get_user_history(tg_id, limit=200)
    if not history_data: return await message.reply("📜 **No Order History Found.**")

    response_text = f"==== Order History for @{user_name} ====\n\n"
    for order in history_data:
        response_text += (f"🆔 Game ID: {order['game_id']}\n🌏 Zone ID: {order['zone_id']}\n💎 Pack: {order['item_name']}\n"
                          f"🆔 Order ID: {order['order_id']}\n📅 Date: {order['date_str']}\n💲 Rate: ${order['price']:,.2f}\n"
                          f"📊 Status: {order['status']}\n────────────────\n")
    
    file_obj = io.BytesIO(response_text.encode('utf-8'))
    file_obj.name = f"History_{tg_id}.txt"
    await message.reply_document(document=file_obj, caption=f"📜 **Order History**\n👤 User: @{user_name}\n📊 Records: {len(history_data)}")

@app.on_message(filters.command("clean") | filters.regex(r"(?i)^\.clean$"))
async def clean_order_history(client, message: Message):
    if not await is_authorized(message): return await message.reply("ɴᴏᴛ ᴀᴜᴛʜᴏʀɪᴢᴇᴅ ᴜsᴇʀ.")
    tg_id = str(message.from_user.id)
    deleted_count = await db.clear_user_history(tg_id)
    if deleted_count > 0: await message.reply(f"🗑️ **History Cleaned Successfully.**\nDeleted {deleted_count} order records from your history.")
    else: await message.reply("📜 **No Order History Found to Clean.**")

# ==========================================
# 🛑 CORE ORDER EXECUTION HELPER
# ==========================================
async def execute_buy_process(client, message, lines, regex_pattern, currency, packages_dict, process_func, title_prefix, is_mcc=False):
    tg_id = str(message.from_user.id)
    telegram_user = message.from_user.username
    username_display = f"@{telegram_user}" if telegram_user else tg_id
    v_bal_key = 'br_balance' if currency == 'BR' else 'ph_balance'
    
    async with user_locks[tg_id]: 
        for line in lines:
            line = line.strip()
            if not line: continue 
            
            match = re.search(regex_pattern, line)
            if not match:
                await message.reply(f"Invalid format: `{line}`\nCheck /help for correct format.")
                continue
                
            game_id = match.group(1)
            zone_id = match.group(2)
            item_input = match.group(3).lower() 
            
            active_packages = None
            if isinstance(packages_dict, list):
                for p_dict in packages_dict:
                    if item_input in p_dict:
                        active_packages = p_dict
                        break
            else:
                if item_input in packages_dict:
                    active_packages = packages_dict
                    
            if not active_packages:
                await message.reply(f"❌ No Package found for '{item_input}'.")
                continue
                
            items_to_buy = active_packages[item_input]
            total_required_price = sum(item['price'] for item in items_to_buy)
            
            user_wallet = await db.get_reseller(tg_id)
            user_v_bal = user_wallet.get(v_bal_key, 0.0) if user_wallet else 0.0
            
            if user_v_bal < total_required_price:
                await message.reply(f"Nᴏᴛ ᴇɴᴏᴜɢʜ ᴍᴏɴᴇʏ ɪɴ ʏᴏᴜʀ ᴠ-ᴡᴀʟʟᴇᴛ.\nNᴇᴇᴅ ʙᴀʟᴀɴᴄᴇ ᴀᴍᴏᴜɴᴛ: {total_required_price} {currency}\nYᴏᴜʀ ʙᴀʟᴀɴᴄᴇ: {user_v_bal} {currency}")
                continue
            
            loading_msg = await message.reply(f"⏱ Order လက်ခံရရှိပါသည်... ခဏစောင့်ပေးပါ ᥫ᭡")
            
            success_count, fail_count, total_spent = 0, 0, 0.0
            order_ids_str, ig_name, error_msg = "", "Unknown", ""
            
            # 🟢 မှတ်ဉာဏ် (Context) သတ်မှတ်ခြင်း
            first_order = True
            prev_context = None 
            
            async with api_semaphore:
                await loading_msg.edit(f"Recharging Diam͟o͟n͟d͟ ● ᥫ᭡")
                for item in items_to_buy:
                    # 🟢 prev_context ကို function ထဲသို့ ထည့်ပို့မည်
                    if is_mcc:
                        result = await process_func(game_id, zone_id, item['pid'], currency, prev_context=prev_context)
                    else:
                        result = await process_func(game_id, zone_id, item['pid'], currency, prev_context=prev_context)
                    
                    if result['status'] == 'success':
                        if first_order:
                            ig_name = result['ig_name']
                            # 🟢 ပထမအကြိမ် အောင်မြင်ပါက Token နှင့် နာမည်ကို မှတ်သားထားမည် (နောက်ပစ္စည်းများအတွက် ID ထပ်မစစ်တော့ပါ)
                            prev_context = {'csrf_token': result['csrf_token'], 'ig_name': ig_name}
                            first_order = False
                            
                        success_count += 1
                        total_spent += item['price']
                        order_ids_str += f"{result['order_id']}\n" 
                        await asyncio.sleep(random.randint(2, 5)) 
                    else:
                        fail_count += 1
                        error_msg = result['message']
                        break 
            
            if success_count > 0:
                now = datetime.datetime.now(MMT)
                date_str = now.strftime("%m/%d/%Y, %I:%M:%S %p")
                
                if currency == 'BR': await db.update_balance(tg_id, br_amount=-total_spent)
                else: await db.update_balance(tg_id, ph_amount=-total_spent)
                
                new_wallet = await db.get_reseller(tg_id)
                new_v_bal = new_wallet.get(v_bal_key, 0.0) if new_wallet else 0.0
                final_order_ids = order_ids_str.strip().replace('\n', ', ')
                
                await db.save_order(
                    tg_id=tg_id, game_id=game_id, zone_id=zone_id, item_name=item_input,
                    price=total_spent, order_id=final_order_ids, status="success"
                )
             
                safe_ig_name = html.escape(str(ig_name))
                safe_username = html.escape(str(username_display))
                
                report = (
                    f"<blockquote><code>**{title_prefix} {game_id} ({zone_id}) {item_input} ({currency})**\n"
                    f"=== ᴛʀᴀɴsᴀᴄᴛɪᴏɴ ʀᴇᴘᴏʀᴛ ===\n\n"
                    f"ᴏʀᴅᴇʀ sᴛᴀᴛᴜs : ✅ Sᴜᴄᴄᴇss\n"
                    f"ɢᴀᴍᴇ ɪᴅ      : {game_id} {zone_id}\n"
                    f"ɪɢ ɴᴀᴍᴇ      : {safe_ig_name}\n"
                    f"sᴇʀɪᴀʟ       :\n{order_ids_str.strip()}\n"
                    f"ɪᴛᴇᴍ         : {item_input} 💎\n"
                    f"sᴘᴇɴᴛ        : {total_spent:.2f} 🪙\n\n"
                    f"ᴅᴀᴛᴇ         : {date_str}\n"
                    f"ᴜsᴇʀɴᴀᴍᴇ     : {safe_username}\n"
                    f"ɪɴɪᴛɪᴀʟ      : ${user_v_bal:,.2f}\n"
                    f"ғɪɴᴀʟ        : ${new_v_bal:,.2f}\n\n"
                    f"Sᴜᴄᴄᴇss {success_count} / Fᴀɪʟ {fail_count}</code></blockquote>"
                )
                await loading_msg.edit(report, parse_mode=ParseMode.HTML)
                if fail_count > 0: await message.reply(f"Only partially successful.\nError: {error_msg}")
            else:
                await loading_msg.edit(f"❌ Order failed:\n{error_msg}")

# ==========================================
# 💎 PURCHASE COMMAND HANDLERS
# ==========================================
@app.on_message(filters.regex(r"(?i)^(?:msc|mlb|br|b)\s+\d+"))
async def handle_br_mlbb(client, message: Message):
    if not await is_authorized(message): return await message.reply(f"ɴᴏᴛ ᴀᴜᴛʜᴏʀɪᴢᴇᴅ ᴜsᴇʀ.❌")
    try:
        lines = message.text.strip().split('\n')
        regex = r"(?i)^(?:msc|mlb|br|b)\s+(\d+)\s*(?:[\(]?\s*(\d+)\s*[\)]?)\s+([a-zA-Z0-9_]+)"
        await execute_buy_process(client, message, lines, regex, 'BR', [DOUBLE_DIAMOND_PACKAGES, BR_PACKAGES], process_smile_one_order, "MLBB")
    except Exception as e: await message.reply(f"System Error: {str(e)}")

@app.on_message(filters.regex(r"(?i)^(?:mlp|ph|p)\s+\d+"))
async def handle_ph_mlbb(client, message: Message):
    if not await is_authorized(message): return await message.reply(f"ɴᴏᴛ ᴀᴜᴛʜᴏʀɪᴢᴇᴅ ᴜsᴇʀ.❌")
    try:
        lines = message.text.strip().split('\n')
        regex = r"(?i)^(?:mlp|ph|p)\s+(\d+)\s*(?:[\(]?\s*(\d+)\s*[\)]?)\s+([a-zA-Z0-9_]+)"
        await execute_buy_process(client, message, lines, regex, 'PH', PH_PACKAGES, process_smile_one_order, "MLBB")
    except Exception as e: await message.reply(f"System Error: {str(e)}")

@app.on_message(filters.regex(r"(?i)^(?:mcc|mcb)\s+\d+"))
async def handle_br_mcc(client, message: Message):
    if not await is_authorized(message): return await message.reply(f"ɴᴏᴛ ᴀᴜᴛʜᴏʀɪᴢᴇᴅ ᴜsᴇʀ.❌")
    try:
        lines = message.text.strip().split('\n')
        regex = r"(?i)^(?:mcc|mcb)\s+(\d+)\s*(?:[\(]?\s*(\d+)\s*[\)]?)\s+([a-zA-Z0-9_]+)"
        await execute_buy_process(client, message, lines, regex, 'BR', MCC_PACKAGES, process_mcc_order, "MCC", is_mcc=True)
    except Exception as e: await message.reply(f"System Error: {str(e)}")

@app.on_message(filters.regex(r"(?i)^mcp\s+\d+"))
async def handle_ph_mcc(client, message: Message):
    if not await is_authorized(message): return await message.reply(f"ɴᴏᴛ ᴀᴜᴛʜᴏʀɪᴢᴇᴅ ᴜsᴇʀ.❌")
    try:
        lines = message.text.strip().split('\n')
        regex = r"(?i)^mcp\s+(\d+)\s*(?:[\(]?\s*(\d+)\s*[\)]?)\s+([a-zA-Z0-9_]+)"
        await execute_buy_process(client, message, lines, regex, 'PH', PH_MCC_PACKAGES, process_mcc_order, "MCC", is_mcc=True)
    except Exception as e: await message.reply(f"System Error: {str(e)}")

# ==========================================
# 📜 PRICE LIST COMMANDS
# ==========================================
def generate_list(package_dict):
    lines = []
    for key, items in package_dict.items():
        total_price = sum(item['price'] for item in items)
        lines.append(f"{key:<5} : ${total_price:,.2f}")
    return "\n".join(lines)

@app.on_message(filters.command("listb") | filters.regex(r"(?i)^\.listb$"))
async def show_price_list_br(client, message: Message):
    if not await is_authorized(message): return await message.reply("ɴᴏᴛ ᴀᴜᴛʜᴏʀɪᴢᴇᴅ ᴜsᴇʀ.")
    response_text = f"🇧🇷 <b>𝘿𝙤𝙪𝙗𝙡𝙚 𝙋𝙖𝙘𝙠𝙖𝙜𝙚𝙨</b>\n<code>{generate_list(DOUBLE_DIAMOND_PACKAGES)}</code>\n\n🇧🇷 <b>𝘽𝙧 𝙋𝙖𝙘𝙠𝙖𝙜𝙚𝙨</b>\n<code>{generate_list(BR_PACKAGES)}</code>"
    await message.reply(response_text, parse_mode=ParseMode.HTML)

@app.on_message(filters.command("listp") | filters.regex(r"(?i)^\.listp$"))
async def show_price_list_ph(client, message: Message):
    if not await is_authorized(message): return await message.reply("ɴᴏᴛ ᴀᴜᴛʜᴏʀɪᴢᴇᴅ ᴜsᴇʀ.")
    response_text = f"🇵🇭 <b>𝙋𝙝 𝙋𝙖𝙘𝙠𝙖𝙜𝙚𝙨</b>\n<code>{generate_list(PH_PACKAGES)}</code>"
    await message.reply(response_text, parse_mode=ParseMode.HTML)

@app.on_message(filters.command("listmb") | filters.regex(r"(?i)^\.listmb$"))
async def show_price_list_mcc(client, message: Message):
    if not await is_authorized(message): return await message.reply("ɴᴏᴛ ᴀᴜᴛʜᴏʀɪᴢᴇᴅ ᴜsᴇʀ.")
    response_text = f"🇧🇷 <b>𝙈𝘾𝘾 𝙋𝘼𝘾𝙆𝘼𝙂𝙀𝙎</b>\n<code>{generate_list(MCC_PACKAGES)}</code>\n\n🇵🇭 <b>𝙋𝙝 𝙈𝘾𝘾 𝙋𝙖𝙘𝙠𝙖𝙜𝙚𝙨</b>\n<code>{generate_list(PH_MCC_PACKAGES)}</code>"
    await message.reply(response_text, parse_mode=ParseMode.HTML)

# ==========================================
# 🧮 SMART CALCULATOR FUNCTION
# ==========================================
@app.on_message(filters.text & filters.regex(r"^[\d\s\.\(\)]+[\+\-\*\/][\d\s\+\-\*\/\(\)\.]+$"))
async def auto_calculator(client, message: Message):
    try:
        expr = message.text.strip()
        if re.match(r"^09[-\s]?\d+", expr): return
        clean_expr = expr.replace(" ", "")
        result = eval(clean_expr, {"__builtins__": None})
        if isinstance(result, float): formatted_result = f"{result:.4f}".rstrip('0').rstrip('.')
        else: formatted_result = str(result)
        await message.reply_text(f"{expr} = {formatted_result}", quote=False)
    except Exception: pass

# ==========================================
# 10. 💓 HEARTBEAT FUNCTION
# ==========================================
async def keep_cookie_alive():
    while True:
        try:
            await asyncio.sleep(2 * 60) 
            scraper = await get_main_scraper()
            headers = {'User-Agent': 'Mozilla/5.0', 'X-Requested-With': 'XMLHttpRequest', 'Origin': 'https://www.smile.one'}
            response = await asyncio.to_thread(scraper.get, 'https://www.smile.one/customer/order', headers=headers)
            if "login" not in response.url.lower() and response.status_code == 200:
                pass 
            else:
                print(f"[{datetime.datetime.now(MMT).strftime('%I:%M %p')}] ⚠️ Main Cookie expired unexpectedly. Reactive Auto-login triggered.")
                try: await app.send_message(OWNER_ID, "⚠️ Cookies Expired unexpectedly. Attempting Auto-Login...", parse_mode=ParseMode.HTML)
                except Exception: pass

                success = await auto_login_and_get_cookie()
                
                if not success:
                    try: await app.send_message(OWNER_ID, "❌ <b>Critical:</b> Reactive Auto-Login failed. Please update cookie manually.", parse_mode=ParseMode.HTML)
                    except Exception: pass
        except Exception: pass


async def schedule_daily_cookie_renewal():
    """ Proactive Renewal: နေ့စဉ် မနက် ၆:၃၀ (MMT) တွင် Cookie အသစ်ကို ကြိုတင်ရယူထားမည်။ """
    while True:
        now = datetime.datetime.now(MMT)
        
        # 🟢 ယနေ့ မနက် ၆:၃၀ အချိန်ကို သတ်မှတ်ခြင်း
        target_time = now.replace(hour=6, minute=30, second=0, microsecond=0)
        
        # 🟢 အကယ်၍ ယနေ့ မနက် ၆:၃၀ ကျော်သွားပြီဆိုလျှင်၊ နောက်နေ့ မနက် ၆:၃၀ အတွက် ပြင်ဆင်မည်
        if now >= target_time:
            target_time += datetime.timedelta(days=1)
            
        # 🟢 မနက် ၆:၃၀ ရောက်ရန် ကျန်ရှိသော စက္ကန့်အရေအတွက်ကို တွက်ချက်ခြင်း
        wait_seconds = (target_time - now).total_seconds()
        print(f"⏰ Proactive Cookie Renewal is scheduled in {wait_seconds / 3600:.2f} hours (at {target_time.strftime('%I:%M %p')} MMT).")
        
        # 🟢 အချိန်ပြည့်သည်အထိ စောင့်နေမည်
        await asyncio.sleep(wait_seconds)
        
        print(f"[{datetime.datetime.now(MMT).strftime('%I:%M %p')}] 🚀 Executing Proactive Cookie Renewal...")
        try: await app.send_message(OWNER_ID, "🔄 <b>System:</b> Executing daily proactive cookie renewal (6:30 AM)...", parse_mode=ParseMode.HTML)
        except Exception: pass

        success = await auto_login_and_get_cookie()
        
        if success:
            try: await app.send_message(OWNER_ID, "✅ <b>System:</b> Proactive cookie renewal successful. Ready for the day!", parse_mode=ParseMode.HTML)
            except Exception: pass
        else:
            try: await app.send_message(OWNER_ID, "❌ <b>System:</b> Proactive cookie renewal failed!", parse_mode=ParseMode.HTML)
            except Exception: pass


# ==========================================
# 🔔 NOTIFICATION SYSTEM (OWNER အား အသိပေးရန်)
# ==========================================
async def notify_owner(text: str):
    try:
        await app.send_message(
            chat_id=OWNER_ID,
            text=text,
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        print(f" Owner ထံသို့ Message ပို့၍မရပါ: {e}")


# ==========================================
# ℹ️ HELP & START COMMANDS
# ==========================================
@app.on_message(filters.command("help") | filters.regex(r"(?i)^\.help$"))
async def send_help_message(client, message: Message):
    is_owner = (message.from_user.id == OWNER_ID)
    help_text = (
        f"<b>🤖 𝐁𝐎𝐓 𝐂𝐎𝐌𝐌𝐀𝐍𝐃𝐒 𝐌𝐄𝐍𝐔</b>\n━━━━━━━━━━━━━━━━\n\n"
        f"<b>💎 𝐌𝐋𝐁Ｂ 𝐃𝐢𝐚𝐦𝐨𝐧𝐝𝐬</b>\n"
        f"🇧🇷 BR MLBB: <code>msc/mlb/br/b ID (Zone) Pack</code>\n"
        f"🇵🇭 PH MLBB: <code>mlp/ph/p ID (Zone) Pack</code>\n\n"
        f"<b>♟️ 𝐌𝐚𝐠𝐢𝐜 𝐂𝐡𝐞𝐬𝐬</b>\n"
        f"🇧🇷 BR MCC: <code>mcc/mcb ID (Zone) Pack</code>\n"
        f"🇵🇭 PH MCC: <code>mcp ID (Zone) Pack</code>\n"
        f"━━━━━━━━━━━━━━━━\n\n"
        f"<b>👤 𝐔𝐬𝐞𝐫 𝐓𝐨𝐨𝐥𝐬</b>\n"
        f"🔹 <code>.balance</code>  : Check Wallet Balance\n"
        f"🔹 <code>.his</code>      : View Order History\n"
        f"🔹 <code>.clean</code>    : Clear History\n"
        f"🔹 <code>.listb</code>     : View BR Price List\n"
        f"🔹 <code>.listp</code>     : View PH Price List\n"
        f"🔹 <code>.listmb</code>    : View MCC Price List\n"
    )
    if is_owner:
        help_text += (
            f"\n<b>👑 𝐎𝐰𝐧𝐞𝐫 𝐂𝐨𝐦𝐦𝐚𝐧𝐝𝐬</b>\n"
            f"🔸 <code>/add ID</code>    : Add User\n"
            f"🔸 <code>/remove ID</code> : Remove User\n"
            f"🔸 <code>/users</code>      : User List\n"
            f"🔸 <code>/setcookie</code> : Update Cookie\n"
        )
    help_text += f"━━━━━━━━━━━━━━━━"
    await message.reply(help_text, parse_mode=ParseMode.HTML)

@app.on_message(filters.command("start"))
async def send_welcome(client, message: Message):
    try:
        tg_id = str(message.from_user.id)
        
        first_name = message.from_user.first_name or ""
        last_name = message.from_user.last_name or ""
        full_name = f"{first_name} {last_name}".strip()
        if not full_name:
            full_name = "User"
            
        safe_full_name = full_name.replace('<', '').replace('>', '')
        username_display = f'<a href="tg://user?id={tg_id}">{safe_full_name}</a>'
        
        EMOJI_1 = "5956355397366320202" # 🥺
        EMOJI_2 = "5954097490109140119" # 👤
        EMOJI_3 = "5958289678837746828" # 🆔
        EMOJI_4 = "5956330306167376831" # 📊
        EMOJI_5 = "5954078884310814346" # 📞

        if await is_authorized(message):
            status = "🟢 Aᴄᴛɪᴠᴇ"
        else:
            status = "🔴 Nᴏᴛ Aᴄᴛɪᴠᴇ"
            
        welcome_text = (
            f"ʜᴇʏ ʙᴀʙʏ <emoji id='{EMOJI_1}'>🥺</emoji>\n\n"
            f"<emoji id='{EMOJI_2}'>👤</emoji> Usᴇʀɴᴀᴍᴇ: {username_display}\n"
            f"<emoji id='{EMOJI_3}'>🆔</emoji> 𝐈𝐃: <code>{tg_id}</code>\n"
            f"<emoji id='{EMOJI_4}'>📊</emoji> Sᴛᴀᴛᴜs: {status}\n\n"
            f"<emoji id='{EMOJI_5}'>📞</emoji> Cᴏɴᴛᴀᴄᴛ ᴜs: @iwillgoforwardsalone"
        )
        
        await message.reply(welcome_text, parse_mode=ParseMode.HTML)
        
    except Exception as e:
        print(f"Start Cmd Error: {e}")
        
        fallback_text = (
            f"ʜᴇʏ ʙᴀʙʏ 🥺\n\n"
            f"👤 Usᴇʀɴᴀᴍᴇ: {full_name}\n"
            f"🆔 𝐈𝐃: <code>{tg_id}</code>\n"
            f"📊 Sᴛᴀᴛᴜs: 🔴 Nᴏᴛ Aᴄᴛɪᴠᴇ\n\n"
            f"📞 Cᴏɴᴛᴀᴄᴛ ᴜs: @iwillgoforwardsalone"
        )
        await message.reply(fallback_text, parse_mode=ParseMode.HTML)

# ==========================================
# 10. RUN BOT
# ==========================================
if __name__ == '__main__':
    print("Starting Heartbeat & Auto-login thread...")
    print("နှလုံးသားမပါရင် ဘယ်အရာမှတရားမဝင်.....")
    
    loop = asyncio.get_event_loop()
    loop.run_until_complete(db.setup_indexes())
    loop.run_until_complete(db.init_owner(OWNER_ID))
    loop.create_task(keep_cookie_alive())

    print("Bot is successfully running (Fully Optimized Asyncio, Pyrofork, Motor & Curl_cffi)...")
    app.run()
