import os
import telebot
import re
import datetime
import cloudscraper
from bs4 import BeautifulSoup
import json
import time
import random
from dotenv import load_dotenv
import threading
from playwright.sync_api import sync_playwright

# ==========================================
# 📌 ENVIRONMENT VARIABLES
# ==========================================
load_dotenv() 

BOT_TOKEN = os.getenv('BOT_TOKEN')
OWNER_ID = int(os.getenv('OWNER_ID', 1318826936)) 
FB_EMAIL = os.getenv('FB_EMAIL')
FB_PASS = os.getenv('FB_PASS')

if not BOT_TOKEN:
    print("❌ Error: .env ဖိုင်ထဲတွင် BOT_TOKEN မပါဝင်ပါ။")
    exit()

MMT = datetime.timezone(datetime.timedelta(hours=6, minutes=30))

# ==========================================
# 1. BOT အခြေခံ အချက်အလက်များ
# ==========================================
bot = telebot.TeleBot(BOT_TOKEN)

# ==========================================
# 🗄️ LOCAL JSON DATABASE
# ==========================================
DB_FILE = 'database.json'

def load_data():
    if not os.path.exists(DB_FILE):
        return {"users": [OWNER_ID], "cookie": "PHPSESSID=205fdnmcd5c6mf0ut2kq4l6ji5"}
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {"users": [OWNER_ID], "cookie": "PHPSESSID=205fdnmcd5c6mf0ut2kq4l6ji5"}

def save_data(data):
    try:
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"❌ Database သိမ်းဆည်းရာတွင် Error: {e}")

initial_data = load_data()
if OWNER_ID not in initial_data["users"]:
    initial_data["users"].append(OWNER_ID)
    save_data(initial_data)

# ==========================================
# 🍪 COOKIES ယူရန် FUNCTION 
# ==========================================
def get_login_cookies():
    db_data = load_data()
    raw_cookie = db_data.get("cookie", "")
    cookie_dict = {}
    for item in raw_cookie.split(';'):
        if '=' in item:
            k, v = item.strip().split('=', 1)
            cookie_dict[k] = v
    return cookie_dict

# ==========================================
# 🤖 PLAYWRIGHT AUTO-LOGIN (FACEBOOK)
# ==========================================
def auto_login_and_get_cookie():
    if not FB_EMAIL or not FB_PASS:
        print("❌ .env တွင် FB_EMAIL နှင့် FB_PASS မရှိပါ။")
        return False
        
    print("🔄 Facebook ဖြင့် Auto-Login ဝင်ပြီး Cookie အသစ် ရှာဖွေနေပါသည်...")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True, 
                args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-blink-features=AutomationControlled']
            )
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={'width': 1280, 'height': 720}
            )
            page = context.new_page()
            
            page.goto("https://www.smile.one/customer/login")
            time.sleep(5) 
            
            with context.expect_page() as popup_info:
                # Facebook Login ခလုတ်ကို နှိပ်ခြင်း
                page.locator("a.login-btn-facebook, a[href*='facebook.com']").first.click()
            
            fb_popup = popup_info.value
            fb_popup.wait_for_load_state()
            
            time.sleep(2)
            fb_popup.fill('input[name="email"]', FB_EMAIL)
            time.sleep(1)
            fb_popup.fill('input[name="pass"]', FB_PASS)
            time.sleep(1)
            
            fb_popup.click('button[name="login"], input[name="login"]')
            
            try:
                page.wait_for_url("**/customer/order**", timeout=30000)
                print("✅ Auto-Login အောင်မြင်ပါသည်။ Cookie ကို သိမ်းဆည်းနေပါသည်...")
                
                cookies = context.cookies()
                cookie_dict = {cookie['name']: cookie['value'] for cookie in cookies}
                raw_cookie_str = "; ".join([f"{k}={v}" for k, v in cookie_dict.items()])
                
                db_data = load_data()
                db_data["cookie"] = raw_cookie_str
                save_data(db_data)
                
                browser.close()
                return True
            except Exception as wait_e:
                print(f"❌ Order စာမျက်နှာသို့ မရောက်ပါ။ (Facebook Checkpoint ဖြစ်နိုင်ပါသည်): {wait_e}")
                browser.close()
                return False
            
    except Exception as e:
        print(f"❌ Auto-Login ပြုလုပ်ရာတွင် အမှားဖြစ်နေပါသည်: {e}")
        return False

# ==========================================
# 📌 PACKAGES
# ==========================================
BR_PACKAGES = {
    '86': [{'pid': '13', 'price': 61.5, 'name': '86 💎'}],
    '172': [{'pid': '23', 'price': 122.00, 'name': '172 💎'}],
    '257': [{'pid': '25', 'price': 177.5, 'name': '257 💎'}],
    '706': [{'pid': '26', 'price': 480.00, 'name': '706 💎'}],
    '2195': [{'pid': '27', 'price': 1453.00, 'name': '2195 💎'}],
    '3688': [{'pid': '28', 'price': 2424.00, 'name': '3688 💎'}],
    '5532': [{'pid': '29', 'price': 3660.00, 'name': '5532 💎'}],
    '9288': [{'pid': '30', 'price': 6079.00, 'name': '9288 💎'}],
    '50': [{'pid': '22590', 'price': 39.0, 'name': '50+50 💎'}],
    '150': [{'pid': '22591', 'price': 116.9, 'name': '150+150 💎'}],
    '250': [{'pid': '22592', 'price': 187.5, 'name': '250+250 💎'}],
    '500': [{'pid': '22593', 'price': 385, 'name': '500+500 💎'}],
    '600': [{'pid': '13', 'price': 61.5, 'name': '86 💎'}, {'pid': '25', 'price': 177.5, 'name': '257 💎'}, {'pid': '25', 'price': 177.5, 'name': '257 💎'}],
    '343': [{'pid': '13', 'price': 61.5, 'name': '86 💎'}, {'pid': '25', 'price': 177.5, 'name': '257 💎'}],
    '429': [{'pid': '23', 'price': 122.00, 'name': '86 💎'}, {'pid': '25', 'price': 177.5, 'name': '257 💎'}],
    '878': [{'pid': '23', 'price': 122.00, 'name': '172 💎'}, {'pid': '26', 'price': 480.00, 'name': '706 💎'}],
    '963': [{'pid': '25', 'price': 177.5, 'name': '257 💎'}, {'pid': '26', 'price': 480.00, 'name': '706 💎'}],
    '1049': [{'pid': '13', 'price': 61.5, 'name': '86 💎'}, {'pid': '25', 'price': 177.5, 'name': '257 💎'}, {'pid': '26', 'price': 480.00, 'name': '706 💎'}],
    '1135': [{'pid': '23', 'price': 122.00, 'name': '172 💎'}, {'pid': '25', 'price': 177.5, 'name': '257 💎'}, {'pid': '26', 'price': 480.00, 'name': '706 💎'}],
    '1412': [{'pid': '26', 'price': 480.00, 'name': '706 💎'}, {'pid': '26', 'price': 480.00, 'name': '706 💎'}],
    '1584': [{'pid': '23', 'price': 122.00, 'name': '172 💎'}, {'pid': '26', 'price': 480.0, 'name': '706 💎'}, {'pid': '26', 'price': 480.00, 'name': '706 💎'}],
    '1755': [{'pid': '13', 'price': 61.5, 'name': '86 💎'}, {'pid': '25', 'price': 177.5, 'name': '257 💎'}, {'pid': '26', 'price': 480.00, 'name': '706 💎'}, {'pid': '26', 'price': 480.00, 'name': '706 💎'}],
    '2538': [{'pid': '13', 'price': 61.5, 'name': '86 💎'}, {'pid': '25', 'price': 177.5, 'name': '257 💎'}, {'pid': '27', 'price': 1453.00, 'name': '2195 💎'}],
    '2901': [{'pid': '27', 'price': 1453.00, 'name': '2195 💎'}, {'pid': '26', 'price': 480.00, 'name': '706 💎'}],
    '3244': [{'pid': '13', 'price': 61.5, 'name': '86 💎'}, {'pid': '25', 'price': 177.5, 'name': '257 💎'}, {'pid': '26', 'price': 480.00, 'name': '706 💎'}, {'pid': '27', 'price': 1453.00, 'name': '2195 💎'}],
    'elite': [{'pid': '26555', 'price': 39.00, 'name': 'Elite Weekly Paackage'}],
    'epic': [{'pid': '26556', 'price': 196.5, 'name': 'Epic Monthly Package'}],
    'tp': [{'pid': '33', 'price': 402.5, 'name': 'Twilight Passage'}],
    'wp': [{'pid': '16642', 'price': 76.00, 'name': 'Weekly Pass'}],
    'wp2': [{'pid': '16642', 'price': 76.00, 'name': 'Weekly Pass'}, {'pid': '16642', 'price': 76.00, 'name': 'Weekly Pass'}],
    'wp3': [{'pid': '16642', 'price': 76.00, 'name': 'Weekly Pass'}, {'pid': '16642', 'price': 76.00, 'name': 'Weekly Pass'}, {'pid': '16642', 'price': 76.00, 'name': 'Weekly Pass'}],
    'wp4': [{'pid': '16642', 'price': 76.00, 'name': 'Weekly Pass'}, {'pid': '16642', 'price': 76.00, 'name': 'Weekly Pass'}, {'pid': '16642', 'price': 76.00, 'name': 'Weekly Pass'}],
    'wp5': [{'pid': '16642', 'price': 76.00, 'name': 'Weekly Pass'}, {'pid': '16642', 'price': 76.00, 'name': 'Weekly Pass'}, {'pid': '16642', 'price': 76.00, 'name': 'Weekly Pass'}, {'pid': '16642', 'price': 76.00, 'name': 'Weekly Pass'}, {'pid': '16642', 'price': 76.00, 'name': 'Weekly Pass'}],
}

PH_PACKAGES = {
    '11': [{'pid': '212', 'price': 9.50, 'name': '11 💎'}],
    '22': [{'pid': '213', 'price': 19.0, 'name': '22 💎'}],
    '56': [{'pid': '214', 'price': 47.50, 'name': '56 💎'}],
    '112': [{'pid': '214', 'price': 47.50, 'name': '56 💎'}, {'pid': '214', 'price': 47.50, 'name': '56 💎'}],
    'wp': [{'pid': '16641', 'price': 95.00, 'name': 'Weekly Pass'}],
}

# ==========================================
# 2. BALANCE အစစ်ယူရန် FUNCTION
# ==========================================
def get_smile_balance(scraper, headers, balance_url='https://www.smile.one/customer/order'):
    balances = {'br_balance': 0.00, 'ph_balance': 0.00}
    try:
        response = scraper.get(balance_url, headers=headers)
        
        br_match = re.search(r'(?i)(?:Balance|Saldo)[\s:]*?<\/p>\s*<p>\s*([\d\.,]+)', response.text)
        if br_match:
            balances['br_balance'] = float(br_match.group(1).replace(',', ''))
        else:
            soup = BeautifulSoup(response.text, 'html.parser')
            main_balance_div = soup.find('div', class_='balance-coins')
            if main_balance_div:
                p_tags = main_balance_div.find_all('p')
                if len(p_tags) >= 2:
                    balances['br_balance'] = float(p_tags[1].text.strip().replace(',', ''))
                    
        ph_match = re.search(r'(?i)Saldo PH[\s:]*?<\/span>\s*<span>\s*([\d\.,]+)', response.text)
        if ph_match:
            balances['ph_balance'] = float(ph_match.group(1).replace(',', ''))
        else:
            soup = BeautifulSoup(response.text, 'html.parser')
            ph_balance_container = soup.find('div', id='all-balance')
            if ph_balance_container:
                span_tags = ph_balance_container.find_all('span')
                if len(span_tags) >= 2:
                    balances['ph_balance'] = float(span_tags[1].text.strip().replace(',', ''))
    except Exception as e:
        pass
    return balances

# ==========================================
# 3. SMILE.ONE SCRAPER FUNCTION 
# ==========================================
def process_smile_one_order(user_id, zone_id, product_id, currency_name):
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    scraper.cookies.update(get_login_cookies())

    # 🌟 Currency (Region) အပေါ်မူတည်ပြီး checkrole API လင့်ခ်များကို ခွဲခြားသတ်မှတ်ခြင်း
    if currency_name == 'PH':
        main_url = 'https://www.smile.one/ph/merchant/mobilelegends'
        checkrole_url = 'https://www.smile.one/ph/merchant/mobilelegends/checkrole'
        query_url = 'https://www.smile.one/ph/merchant/mobilelegends/query'
        pay_url = 'https://www.smile.one/ph/merchant/mobilelegends/pay'
        order_api_url = 'https://www.smile.one/ph/customer/activationcode/codelist'
        balance_url = 'https://www.smile.one/ph/customer/order'
    else:
        main_url = 'https://www.smile.one/merchant/mobilelegends'
        checkrole_url = 'https://www.smile.one/merchant/mobilelegends/checkrole'
        query_url = 'https://www.smile.one/merchant/mobilelegends/query'
        pay_url = 'https://www.smile.one/merchant/mobilelegends/pay'
        order_api_url = 'https://www.smile.one/customer/activationcode/codelist'
        balance_url = 'https://www.smile.one/customer/order'
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest', 
        'Referer': main_url, 
        'Origin': 'https://www.smile.one'
    }

    try:
        response = scraper.get(main_url, headers=headers)
        
        if response.status_code in [403, 503] or "cloudflare" in response.text.lower() or "security verification" in response.text.lower():
             return {"status": "error", "message": "⚠️ Cloudflare လုံခြုံရေးမှ Bot အား Block ထားပါသည်။ Browser မှ Cookie အသစ် ပြန်ယူထည့်ပါ။"}

        soup = BeautifulSoup(response.text, 'html.parser')
        
        csrf_token = None
        meta_tag = soup.find('meta', {'name': 'csrf-token'})
        if meta_tag: csrf_token = meta_tag.get('content')
        else:
            csrf_input = soup.find('input', {'name': '_csrf'})
            if csrf_input: csrf_token = csrf_input.get('value')

        if not csrf_token: return {"status": "error", "message": "CSRF Token ရှာမတွေ့ပါ။ /setcookie ဖြင့် Cookie အသစ်ထည့်ပါ။"}

        # 🌟 ငွေမချေခင် ID အရင်မှန်မမှန် Check Role ဖြင့် စစ်ဆေးခြင်း
        check_data = {
            'user_id': user_id, 
            'zone_id': zone_id, 
            '_csrf': csrf_token
        }
        
        role_response = scraper.post(checkrole_url, data=check_data, headers=headers)
        try:
            role_result = role_response.json()
            ig_name = role_result.get('username') or role_result.get('data', {}).get('username')
            if not ig_name or str(ig_name).strip() == "":
                real_error = role_result.get('msg') or role_result.get('message') or "အကောင့်ရှာမတွေ့ပါ။"
                return {"status": "error", "message": f"❌ အကောင့် မှားယွင်းနေပါသည်: {real_error}"}
        except Exception:
            return {"status": "error", "message": "⚠️ Check Role API Error: အကောင့်စစ်ဆေး၍မရပါ။"}
        # -----------------------------------------------------------

        # အကောင့်မှန်ကန်မှသာ Flow ID ယူပြီး ဆက်လုပ်မည်
        query_data = {
            'user_id': user_id, 'zone_id': zone_id, 'pid': product_id,
            'checkrole': '', 'pay_methond': 'smilecoin', 'channel_method': 'smilecoin', '_csrf': csrf_token
        }
        
        query_response = scraper.post(query_url, data=query_data, headers=headers)
        
        try: 
            query_result = query_response.json()
        except Exception: 
            if "cloudflare" in query_response.text.lower() or "just a moment" in query_response.text.lower():
                return {"status": "error", "message": "⚠️ Query တွင် Cloudflare မှ Block ထားပါသည်။"}
            return {"status": "error", "message": f"Query API Error (Status: {query_response.status_code})"}
            
        flowid = query_result.get('flowid') or query_result.get('data', {}).get('flowid')
        
        if not flowid:
            raw_debug = json.dumps(query_result, ensure_ascii=False)
            real_error = query_result.get('msg') or query_result.get('message') or ""
            
            if "login" in str(real_error).lower() or "unauthorized" in str(real_error).lower():
                return {"status": "error", "message": "⚠️ Cookie သက်တမ်းကုန်သွားပါပြီ။ ကျေးဇူးပြု၍ `/setcookie` ဖြင့် အသစ်ထည့်ပါ။"}
            else:
                err_text = real_error if real_error else "အကောင့်ရှာမတွေ့ပါ သို့မဟုတ် ငြင်းပယ်ခံရသည်။"
                return {"status": "error", "message": f"Smile.one ၏ တုံ့ပြန်ချက်: {err_text}\n\n*(Debug: {raw_debug})*"}

        current_balances = get_smile_balance(scraper, headers, balance_url)

        pay_data = {
            '_csrf': csrf_token, 'user_id': user_id, 'zone_id': zone_id, 'pay_methond': 'smilecoin',
            'product_id': product_id, 'channel_method': 'smilecoin', 'flowid': flowid, 'email': '', 'coupon_id': ''
        }
        
        pay_response = scraper.post(pay_url, data=pay_data, headers=headers)
        pay_text = pay_response.text.lower()
        
        if "saldo insuficiente" in pay_text or "insufficient" in pay_text:
            return {"status": "error", "message": "သင့်အကောင့်တွင် ငွေ (Balance) မလုံလောက်ပါ။"}
        
        time.sleep(2) 
        
        real_order_id = "ရှာမတွေ့ပါ"
        is_success = False

        api_params = {'type': 'orderlist', 'p': '1', 'pageSize': '5'}
        try:
            hist_res = scraper.get(order_api_url, params=api_params, headers=headers)
            hist_json = hist_res.json()
            
            if 'list' in hist_json and isinstance(hist_json['list'], list) and len(hist_json['list']) > 0:
                for order in hist_json['list']:
                    if str(order.get('user_id')) == str(user_id) and str(order.get('server_id')) == str(zone_id):
                        if str(order.get('order_status', '')).lower() == 'success' or str(order.get('status')) == '1':
                            real_order_id = str(order.get('increment_id', "ရှာမတွေ့ပါ"))
                            is_success = True
                            break
        except Exception as e:
            pass

        if not is_success:
            try:
                pay_json = pay_response.json()
                code = str(pay_json.get('code', ''))
                status = str(pay_json.get('status', ''))
                msg = str(pay_json.get('msg', '')).lower()
                if code in ['200', '0', '1'] or status in ['200', '0', '1'] or msg in ['success', 'ok', 'sucesso'] or 'success' in pay_text:
                    is_success = True
            except:
                if 'success' in pay_text or 'ok' in pay_text or 'sucesso' in pay_text:
                    is_success = True

        if is_success:
            return {"status": "success", "ig_name": ig_name, "order_id": real_order_id, "balances": current_balances}
        else:
            err_msg = "ငွေချေမှု မအောင်မြင်ပါ။"
            try:
                err_json = pay_response.json()
                raw_pay_debug = json.dumps(err_json, ensure_ascii=False)
                if 'msg' in err_json: 
                    err_msg = f"ငွေချေမှု မအောင်မြင်ပါ။ ({err_json['msg']})\n\n*(Debug: {raw_pay_debug})*"
            except: pass
            return {"status": "error", "message": err_msg}

    except Exception as e: return {"status": "error", "message": f"System Error: {str(e)}"}

# ==========================================
# 4. 🛡️ AUTHORIZATION စစ်ဆေးရန် FUNCTION
# ==========================================
def is_authorized(message):
    if message.from_user.id == OWNER_ID:
        return True
    
    db_data = load_data()
    if message.from_user.id in db_data.get("users", []):
        return True
        
    if message.from_user.username:
        username = message.from_user.username.lower()
        if username in db_data.get("users", []):
            return True
            
    return False

# ==========================================
# 10. 💓 HEARTBEAT (SESSION KEEP-ALIVE) FUNCTION
# ==========================================
def keep_cookie_alive():
    while True:
        try:
            time.sleep(10 * 60) # ၅ မိနစ် တစ်ခါ run မည်
            scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
            scraper.cookies.update(get_login_cookies())
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'X-Requested-With': 'XMLHttpRequest',
                'Origin': 'https://www.smile.one'
            }
            
            response = scraper.get('https://www.smile.one/customer/order', headers=headers)
            
            if "login" not in response.url.lower() and response.status_code == 200:
                print(f"[{datetime.datetime.now(MMT).strftime('%I:%M %p')}] 💓 Heartbeat: Session is alive!")
            else:
                print(f"[{datetime.datetime.now(MMT).strftime('%I:%M %p')}] ⚠️ Heartbeat: Session expired. Will auto-login on next request.")
        except Exception as e:
            print(f"❌ Heartbeat Error: {e}")

# ==========================================
# 5. OWNER COMMANDS (Users / Cookies)
# ==========================================
@bot.message_handler(commands=['add'])
def add_user(message):
    if message.from_user.id != OWNER_ID: return bot.reply_to(message, "❌ သင်သည် Owner မဟုတ်ပါ။")
    
    parts = message.text.split()
    if len(parts) < 2:
        return bot.reply_to(message, "⚠️ အသုံးပြုရန် ပုံစံ - `/add <user_id သို့မဟုတ် @username>`", parse_mode="Markdown")
        
    target = parts[1].strip()
    db_data = load_data()
    
    try:
        if target.startswith('@') or not target.isdigit():
            username = target.replace('@', '').lower()
            if username in db_data["users"]:
                bot.reply_to(message, f"⚠️ Username `@{username}` သည် စာရင်းထဲတွင် ရှိပြီးသားဖြစ်ပါသည်။", parse_mode="Markdown")
            else:
                db_data["users"].append(username)
                save_data(db_data)
                bot.reply_to(message, f"✅ Username `@{username}` ကို ခွင့်ပြုလိုက်ပါပြီ။", parse_mode="Markdown")
        else:
            new_user_id = int(target)
            if new_user_id in db_data["users"]:
                bot.reply_to(message, f"⚠️ User ID `{new_user_id}` သည် စာရင်းထဲတွင် ရှိပြီးသားဖြစ်ပါသည်။", parse_mode="Markdown")
            else:
                db_data["users"].append(new_user_id)
                save_data(db_data)
                bot.reply_to(message, f"✅ User ID `{new_user_id}` ကို ခွင့်ပြုလိုက်ပါပြီ။", parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['remove'])
def remove_user(message):
    if message.from_user.id != OWNER_ID: return bot.reply_to(message, "❌ သင်သည် Owner မဟုတ်ပါ။")
    
    parts = message.text.split()
    if len(parts) < 2:
        return bot.reply_to(message, "⚠️ အသုံးပြုရန် ပုံစံ - `/remove <user_id သို့မဟုတ် @username>`", parse_mode="Markdown")
        
    target = parts[1].strip()
    db_data = load_data()
    
    try:
        if target.startswith('@') or not target.isdigit():
            username = target.replace('@', '').lower()
            if username in db_data["users"]:
                db_data["users"].remove(username)
                save_data(db_data)
                bot.reply_to(message, f"✅ Username `@{username}` ကို ပိတ်လိုက်ပါပြီ။", parse_mode="Markdown")
            else:
                bot.reply_to(message, "❌ ထို Username သည် စာရင်းထဲတွင် မရှိပါ။")
        else:
            remove_user_id = int(target)
            if remove_user_id == OWNER_ID: return bot.reply_to(message, "❌ Owner ကို ပြန်ဖြုတ်၍ မရပါ။")
            
            if remove_user_id in db_data["users"]:
                db_data["users"].remove(remove_user_id)
                save_data(db_data)
                bot.reply_to(message, f"✅ User ID `{remove_user_id}` ကို ပိတ်လိုက်ပါပြီ။", parse_mode="Markdown")
            else:
                bot.reply_to(message, "❌ ထို User ID သည် စာရင်းထဲတွင် မရှိပါ။")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['users'])
def list_users(message):
    if message.from_user.id != OWNER_ID: return bot.reply_to(message, "❌ သင်သည် Owner မဟုတ်ပါ။")
    
    db_data = load_data()
    user_list = []
    
    for u in db_data.get("users", []):
        if str(u).isdigit():
            role = "owner" if int(u) == OWNER_ID else "user"
            user_list.append(f"🔹 ID: `{u}` ({role})")
        else:
            user_list.append(f"🔹 Username: `@{u}` (user)")
            
    final_text = "\n".join(user_list) if user_list else "No users found."
    bot.reply_to(message, f"📋 **ခွင့်ပြုထားသော User စာရင်း:**\n{final_text}", parse_mode="Markdown")

@bot.message_handler(commands=['setcookie'])
def set_cookie_command(message):
    if message.from_user.id != OWNER_ID: 
        return bot.reply_to(message, "❌ သင်သည် Owner မဟုတ်ပါ။")
        
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        return bot.reply_to(message, "⚠️ **အသုံးပြုရန် ပုံစံ:**\n`/setcookie <Cookie_အရှည်ကြီး>`", parse_mode="Markdown")
    
    raw_cookie_str = parts[1].strip()
    try:
        db_data = load_data()
        db_data["cookie"] = raw_cookie_str
        save_data(db_data)
        bot.reply_to(message, f"✅ **Cookie အသစ်ကို လုံခြုံစွာ မှတ်သားလိုက်ပါပြီ။**", parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"❌ Cookie သိမ်းဆည်းရာတွင် အမှားဖြစ်နေပါသည်:\n{str(e)}")

@bot.message_handler(commands=['balance'])
def check_balance_command(message):
    if not is_authorized(message): return bot.reply_to(message, "❌ အသုံးပြုခွင့် မရှိပါ။")
    loading_msg = bot.reply_to(message, "⏳ လက်ကျန်ငွေ (Balance) ကို ဆွဲယူနေပါသည်...")
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    scraper.cookies.update(get_login_cookies()) 
    headers = {'X-Requested-With': 'XMLHttpRequest', 'Origin': 'https://www.smile.one'}
    try:
        balances = get_smile_balance(scraper, headers, 'https://www.smile.one/customer/order')
        report = f"Balance (BR): ${balances.get('br_balance', 0.00):,.2f}\nBalance (PH): ${balances.get('ph_balance', 0.00):,.2f}"
        bot.edit_message_text(chat_id=message.chat.id, message_id=loading_msg.message_id, text=report)
    except Exception as e:
        bot.edit_message_text(chat_id=message.chat.id, message_id=loading_msg.message_id, text=f"❌ Error:\n{str(e)}")

# ==========================================
# 6. 📌 ACTIVATION CODE ထည့်ရန် COMMAND
# ==========================================
@bot.message_handler(func=lambda message: re.match(r"(?i)^/(activecodebr|activecodeph)\b", message.text.strip()))
def handle_activecode(message):
    if not is_authorized(message): return bot.reply_to(message, "❌ အသုံးပြုခွင့် မရှိပါ။")
    
    match = re.search(r"(?i)^/(activecodebr|activecodeph)\s+([a-zA-Z0-9]+)", message.text.strip())
    
    if not match: 
        return bot.reply_to(message, "⚠️ အသုံးပြုရန် ပုံစံ - `/activecodebr <Code>` သို့မဟုတ် `/activecodeph <Code>`", parse_mode="Markdown")
    
    command_used = match.group(1).lower()
    activation_code = match.group(2).strip()
    
    if command_used == 'activecodeph':
        page_url = 'https://www.smile.one/ph/customer/activationcode'
        check_url = 'https://www.smile.one/ph/smilecard/pay/checkcard'
        pay_url = 'https://www.smile.one/ph/smilecard/pay/payajax'
        base_origin = 'https://www.smile.one'
        base_referer = 'https://www.smile.one/ph/'
        api_type = "PH"
    else:
        page_url = 'https://www.smile.one/customer/activationcode'
        check_url = 'https://www.smile.one/smilecard/pay/checkcard'
        pay_url = 'https://www.smile.one/smilecard/pay/payajax'
        base_origin = 'https://www.smile.one'
        base_referer = 'https://www.smile.one/'
        api_type = "BR"

    loading_msg = bot.reply_to(message, f"⏳ {api_type} Region အတွက် Code `{activation_code}` ကို စစ်ဆေးနေပါသည်...", parse_mode="Markdown")
    
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    scraper.cookies.update(get_login_cookies())
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Referer': base_referer,
    }

    try:
        res = scraper.get(page_url, headers=headers)
        
        if "Just a moment" in res.text or "Cloudflare" in res.text:
            return bot.edit_message_text(chat_id=message.chat.id, message_id=loading_msg.message_id, text="❌ **Cloudflare Blocked!** Cookie ပြန်ထည့်ပါ။")
            
        if "login" in res.url.lower():
            return bot.edit_message_text(chat_id=message.chat.id, message_id=loading_msg.message_id, text="❌ **Session Expired!** Cookie သက်တမ်းကုန်နေပါသည်။ `/setcookie` ဖြင့် အသစ်ပြန်ထည့်ပေးပါ။")

        soup = BeautifulSoup(res.text, 'html.parser')
        csrf_token = None
        
        csrf_input = soup.find('input', {'name': '_csrf'})
        if csrf_input: csrf_token = csrf_input.get('value')
            
        if not csrf_token:
            meta_tag = soup.find('meta', {'name': 'csrf-token'})
            if meta_tag: csrf_token = meta_tag.get('content')

        if not csrf_token: 
            return bot.edit_message_text(chat_id=message.chat.id, message_id=loading_msg.message_id, text="❌ CSRF Token မရရှိပါ။")

        ajax_headers = headers.copy()
        ajax_headers.update({
            'X-Requested-With': 'XMLHttpRequest',
            'Origin': base_origin,
            'Referer': page_url,
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        })

        payload = {'_csrf': csrf_token, 'pin': activation_code}
        check_res = scraper.post(check_url, data=payload, headers=ajax_headers)
        
        try:
            check_json = check_res.json()
        except Exception:
            return bot.edit_message_text(chat_id=message.chat.id, message_id=loading_msg.message_id, text=f"❌ **API Error!** JSON ပြန်မလာပါ။\nHTTP Status: {check_res.status_code}")

        code_status = str(check_json.get('code', check_json.get('status', '')))
        code_msg = str(check_json.get('msg', check_json.get('message', '')))
        
        raw_debug = json.dumps(check_json, ensure_ascii=False) 

        # '201' (Confirm လုပ်ရန်တောင်းဆိုခြင်း) ကိုပါ အောင်မြင်သည်ဟု သတ်မှတ်မည်
        if code_status in ['200', '201', '0', '1'] or 'success' in code_msg.lower() or 'ok' in code_msg.lower():
            bot.edit_message_text(chat_id=message.chat.id, message_id=loading_msg.message_id, text=f"⏳ Code မှန်ကန်ပါသည်။ ငွေသွင်းနေပါသည်...", parse_mode="Markdown")
            
            pay_payload = {'_csrf': csrf_token, 'sec': activation_code} 
            pay_res = scraper.post(pay_url, data=pay_payload, headers=ajax_headers)
            
            try:
                pay_json = pay_res.json()
            except Exception:
                return bot.edit_message_text(chat_id=message.chat.id, message_id=loading_msg.message_id, text=f"❌ **Redeem API Error!**\nHTTP Status: {pay_res.status_code}")

            pay_status = str(pay_json.get('code', pay_json.get('status', '')))
            pay_msg = str(pay_json.get('msg', pay_json.get('message', '')))
            raw_pay_debug = json.dumps(pay_json, ensure_ascii=False)
            
            if pay_status in ['200', '0', '1'] or 'success' in pay_msg.lower() or 'ok' in pay_msg.lower():
                bot.edit_message_text(chat_id=message.chat.id, message_id=loading_msg.message_id, text=f"✅ **Activation Success!**\nCode `{activation_code}` ကို အောင်မြင်စွာ ထည့်သွင်းပြီးပါပြီ ({api_type})။", parse_mode="Markdown")
            else:
                err_text = pay_msg if pay_msg else "အကြောင်းရင်း မသိရပါ"
                bot.edit_message_text(chat_id=message.chat.id, message_id=loading_msg.message_id, text=f"❌ **Redeem Failed!**\nအကြောင်းရင်း: {err_text}\n\n*(Debug Data: {raw_pay_debug})*")
        else:
            if code_status == '201':
                err_text = "Code မှားနေပါသည် (သို့) Region လွဲနေပါသည်"
            else:
                err_text = code_msg if code_msg else "အကြောင်းရင်း မသိရပါ"
                
            bot.edit_message_text(chat_id=message.chat.id, message_id=loading_msg.message_id, text=f"❌ **Check Failed!**\nအကြောင်းရင်း: {err_text}\n\n*(Debug Data: {raw_debug})*")

    except Exception as e:
        bot.edit_message_text(chat_id=message.chat.id, message_id=loading_msg.message_id, text=f"❌ Error: {str(e)}")

# ==========================================
# 7. 📌 ROLE စစ်ဆေးရန် COMMAND (With Auto-Retry)
# ==========================================
@bot.message_handler(func=lambda message: re.match(r"(?i)^/?role\b", message.text.strip()))
def handle_check_role(message):
    if not is_authorized(message):
        return bot.reply_to(message, "❌ အသုံးပြုခွင့် မရှိပါ။", parse_mode="Markdown")

    match = re.search(r"(?i)^/?role\s+(\d+)\s*\(\s*(\d+)\s*\)", message.text.strip())
    if not match:
        return bot.reply_to(message, "❌ Format မှားယွင်းနေပါသည်:\n(ဥပမာ - `/role 184224272 (2931)`)", parse_mode="Markdown")

    game_id = match.group(1).strip()
    zone_id = match.group(2).strip()
    
    loading_msg = bot.reply_to(message, "⏳ အကောင့်နှင့် Region ကို ရှာဖွေနေပါသည်...")

    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    scraper.cookies.update(get_login_cookies())
    
    main_url = 'https://www.smile.one/merchant/mobilelegends'
    checkrole_url = 'https://www.smile.one/merchant/mobilelegends/checkrole'
    headers = {'X-Requested-With': 'XMLHttpRequest', 'Referer': main_url, 'Origin': 'https://www.smile.one'}

    try:
        # --- 1. Smile.one မှ IGN စစ်ဆေးခြင်း ---
        res = scraper.get(main_url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        csrf_token = None
        meta_tag = soup.find('meta', {'name': 'csrf-token'})
        if meta_tag: csrf_token = meta_tag.get('content')
        else:
            csrf_input = soup.find('input', {'name': '_csrf'})
            if csrf_input: csrf_token = csrf_input.get('value')

        if not csrf_token:
            return bot.edit_message_text(chat_id=message.chat.id, message_id=loading_msg.message_id, text="❌ CSRF Token ရှာမတွေ့ပါ။ /setcookie ဖြင့် Cookie အသစ်ထည့်ပါ။")

        check_data = {
            'user_id': game_id, 
            'zone_id': zone_id, 
            '_csrf': csrf_token
        }
        
        role_response = scraper.post(checkrole_url, data=check_data, headers=headers)
        
        try: 
            role_result = role_response.json()
        except: 
            return bot.edit_message_text(chat_id=message.chat.id, message_id=loading_msg.message_id, text="❌ စစ်ဆေး၍မရပါ။ (Smile API Error)")
            
        ig_name = role_result.get('username') or role_result.get('data', {}).get('username')
        
        if not ig_name or str(ig_name).strip() == "":
            real_error = role_result.get('msg') or role_result.get('message') or "အကောင့်ရှာမတွေ့ပါ။"
            if "login" in str(real_error).lower() or "unauthorized" in str(real_error).lower():
                return bot.edit_message_text(chat_id=message.chat.id, message_id=loading_msg.message_id, text="⚠️ Cookie သက်တမ်းကုန်သွားပါပြီ။ ကျေးဇူးပြု၍ `/setcookie` ဖြင့် အသစ်ထည့်ပါ။")
            return bot.edit_message_text(chat_id=message.chat.id, message_id=loading_msg.message_id, text=f"❌ **အကောင့် မှားယွင်းနေပါသည်:**\n{real_error}")

        smile_region = role_result.get('zone') or role_result.get('region') or role_result.get('data', {}).get('zone') or "Unknown"

        # --- 2. Pizzoshop မှ Region (နိုင်ငံ) အတိအကျကို ထပ်မံဆွဲယူခြင်း ---
        pizzo_region = "Unknown"
        try:
            pizzo_headers = {
                'authority': 'pizzoshop.com',
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'content-type': 'application/x-www-form-urlencoded',
                'origin': 'https://pizzoshop.com',
                'referer': 'https://pizzoshop.com/mlchecker',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            scraper.get("https://pizzoshop.com/mlchecker", headers=pizzo_headers, timeout=10)
            payload = {'user_id': game_id, 'zone_id': zone_id}
            
            pizzo_res = scraper.post("https://pizzoshop.com/mlchecker/check", data=payload, headers=pizzo_headers, timeout=15)
            pizzo_soup = BeautifulSoup(pizzo_res.text, 'html.parser')
            table = pizzo_soup.find('table', class_='table-modern')
            
            if table:
                rows = table.find_all('tr')
                for row in rows:
                    th = row.find('th')
                    td = row.find('td')
                    if th and td:
                        header = th.get_text(strip=True).lower()
                        value = td.get_text(strip=True)
                        if 'region id' in header or 'region' in header:
                            pizzo_region = value
        except Exception as e:
            pass # Pizzoshop ဘက်က Error တက်ပါက ကျော်သွားမည်

        # Pizzoshop မှ နိုင်ငံနာမည်ရပါက ၎င်းကိုသုံးမည်၊ မရပါက Smile.one ၏ မူလ Region ကိုသာ ပြမည်
        final_region = pizzo_region if pizzo_region != "Unknown" else smile_region

        # --- 3. အချက်အလက်များကို ပေါင်းစပ်ထုတ်ပေးခြင်း ---
        report = f"ɢᴀᴍᴇ ɪᴅ : {game_id} ({zone_id})\n"
        report += f"ɪɢɴ ɴᴀᴍᴇ : {ig_name}\n"
        report += f"ʀᴇɢɪᴏɴ : {final_region}"

        bot.edit_message_text(chat_id=message.chat.id, message_id=loading_msg.message_id, text=report)

    except Exception as e:
        bot.edit_message_text(chat_id=message.chat.id, message_id=loading_msg.message_id, text=f"❌ System Error: {str(e)}")

# ==========================================
# 8. COMMAND HANDLER (Multi-line / WP Combo)
# ==========================================
@bot.message_handler(func=lambda message: re.match(r"(?i)^(br|bro|ph|pho)\s+\d+", message.text.strip()))
def handle_direct_buy(message):
    if not is_authorized(message):
        return bot.reply_to(message, f"❌ သင့်တွင် ဤ Bot ကို အသုံးပြုခွင့် မရှိပါ။", parse_mode="Markdown")

    try:
        lines = message.text.strip().split('\n')
        telegram_user = message.from_user.username
        username_display = f"@{telegram_user}" if telegram_user else "Unknown"
        
        for line in lines:
            line = line.strip()
            if not line: continue 
                
            match = re.search(r"(?i)^(br|bro|ph|pho)\s*(\d+)\s*\(\s*(\d+)\s*\)\s*([a-zA-Z0-9]+)", line)
            if not match:
                bot.reply_to(message, f"❌ Format မှားယွင်းနေပါသည်: `{line}`\n(ဥပမာ - br 12345678 (1234) wp)", parse_mode="Markdown")
                continue
                
            command_prefix = match.group(1)
            game_id = match.group(2)
            zone_id = match.group(3)
            item_input = match.group(4).lower() 
            
            if command_prefix and command_prefix.lower() in ['ph', 'pho']:
                currency_name = 'PH'
                active_packages = PH_PACKAGES
                used_balance_key = 'ph_balance'
                display_prefix = command_prefix.lower()
            else:
                currency_name = 'BR'
                active_packages = BR_PACKAGES
                used_balance_key = 'br_balance'
                display_prefix = command_prefix.lower() if command_prefix else 'br'
            
            if item_input not in active_packages:
                bot.reply_to(message, f"❌ ရွေးချယ်ထားသော '{item_input}' အတွက် Package မရှိပါ။")
                continue
                
            items_to_buy = active_packages[item_input]
            
            loading_msg = bot.reply_to(message, f"⏳ `{display_prefix} {game_id} ({zone_id}) {item_input}` အတွက် Order တင်နေပါသည်...", parse_mode="Markdown")
            
            order_ids_str = ""
            total_price = 0.0
            success_count = 0
            fail_count = 0
            ig_name = "Unknown"
            initial_used_balance = 0.0
            error_msg = ""
            first_order = True
            
            for item in items_to_buy:
                product_id = item['pid']
                item_price = item['price']
                
                result = process_smile_one_order(game_id, zone_id, product_id, currency_name)
                
                if result['status'] == 'success':
                    if first_order:
                        initial_used_balance = result['balances'][used_balance_key]
                        ig_name = result['ig_name']
                        first_order = False
                    
                    success_count += 1
                    total_price += item_price
                    order_ids_str += f"Order ID:\n{result['order_id']}\n"
                    
                    wait_time = random.randint(5, 10)
                    time.sleep(wait_time) 
                else:
                    fail_count += 1
                    error_msg = result['message']
                    break 
            
            if success_count > 0:
                now = datetime.datetime.now(MMT)
                date_str = now.strftime("%m/%d/%Y, %I:%M:%S %p")
                final_used_balance = initial_used_balance - total_price
                
                report = f"{display_prefix} {game_id} ({zone_id}) {item_input}\n"
                report += "=== ᴛʀᴀɴsᴀᴄᴛɪᴏɴ ʀᴇᴘᴏʀᴛ ===\n\n"
                report += "ᴏʀᴅᴇʀ sᴛᴀᴛᴜs: ✅ SUCCESS\n"
                report += f"ɢᴀᴍᴇ ɪᴅ: {game_id} {zone_id}\n"
                report += f"ɪɢ ɴᴀᴍᴇ: {ig_name}\n"
                report += order_ids_str
                report += f"ɪᴛᴇᴍ: {item_input} 💎\n"
                report += f"ᴛᴏᴛᴀʟ ᴀᴍᴏᴜɴᴛ: {total_price:.2f} 🪙\n\n"
                report += f"ᴅᴀᴛᴇ: {date_str}\n"
                report += f"ᴜsᴇʀɴᴀᴍᴇ: {username_display}\n"
                report += f"ᴛᴏᴛᴀʟ sᴘᴇɴᴛ: ${total_price:.2f}\n"
                report += f"ɪɴɪᴛɪᴀʟ ʙᴀʟᴀɴᴄᴇ ({currency_name}): ${initial_used_balance:,.2f}\n"
                report += f"ғɪɴᴀʟ ʙᴀʟᴀɴᴄᴇ ({currency_name}): ${final_used_balance:,.2f}\n\n"
                report += f"sᴜᴄᴄᴇss {success_count} / Fail {fail_count}" 

                bot.edit_message_text(chat_id=message.chat.id, message_id=loading_msg.message_id, text=report)
                
                if fail_count > 0:
                    bot.reply_to(message, f"⚠️ အချို့သာ အောင်မြင်ပါသည်။\nError: {error_msg}")
            else:
                bot.edit_message_text(chat_id=message.chat.id, message_id=loading_msg.message_id, text=f"❌ Order မအောင်မြင်ပါ:\n{error_msg}")

    except Exception as e:
        bot.reply_to(message, f"System Error: {str(e)}")

# ==========================================
# 9. START BOT / DEFAULT COMMAND
# ==========================================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Contact us @iwillgoforwardsalone")

if __name__ == '__main__':
    print("Clearing old webhooks if any...")
    try:
        bot.remove_webhook()
        time.sleep(1)
    except:
        pass
        
    print("Starting Heartbeat thread for Session Keep-Alive...")
    threading.Thread(target=keep_cookie_alive, daemon=True).start()

    print("Bot is successfully running (With Playwright Auto-Login)...")
    bot.infinity_polling()
