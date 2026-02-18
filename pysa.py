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

# Database ဖိုင်ကို လှမ်းခေါ်ခြင်း
import database as db

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
bot = telebot.TeleBot(BOT_TOKEN)
transaction_lock = threading.Lock()

# Owner အကောင့်ကို Database ထဲ အစပြုပေးမည်
db.init_owner(OWNER_ID)

# ==========================================
# 🍪 MAIN SCRAPER (OWNER'S COOKIE ONLY)
# ==========================================
def get_main_scraper():
    raw_cookie = db.get_main_cookie()
    cookie_dict = {}
    if raw_cookie:
        for item in raw_cookie.split(';'):
            if '=' in item:
                k, v = item.strip().split('=', 1)
                cookie_dict[k] = v
                
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    if cookie_dict:
        scraper.cookies.update(cookie_dict)
    return scraper

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
                
                db.update_main_cookie(raw_cookie_str)
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
    except Exception: pass
    return balances

# ==========================================
# 3. SMILE.ONE SCRAPER FUNCTION 
# ==========================================
def process_smile_one_order(game_id, zone_id, product_id, currency_name):
    scraper = get_main_scraper()

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
        if response.status_code in [403, 503] or "cloudflare" in response.text.lower():
             return {"status": "error", "message": "⚠️ Cloudflare Block ထားပါသည်။"}

        soup = BeautifulSoup(response.text, 'html.parser')
        csrf_token = None
        meta_tag = soup.find('meta', {'name': 'csrf-token'})
        if meta_tag: csrf_token = meta_tag.get('content')
        else:
            csrf_input = soup.find('input', {'name': '_csrf'})
            if csrf_input: csrf_token = csrf_input.get('value')

        if not csrf_token: return {"status": "error", "message": "CSRF Token ရှာမတွေ့ပါ။ /setcookie ဖြင့် Cookie အသစ်ထည့်ပါ။"}

        check_data = {'user_id': game_id, 'zone_id': zone_id, '_csrf': csrf_token}
        role_response = scraper.post(checkrole_url, data=check_data, headers=headers)
        try:
            role_result = role_response.json()
            ig_name = role_result.get('username') or role_result.get('data', {}).get('username')
            if not ig_name or str(ig_name).strip() == "":
                real_error = role_result.get('msg') or role_result.get('message') or "အကောင့်ရှာမတွေ့ပါ။"
                return {"status": "error", "message": f"❌ အကောင့် မှားယွင်းနေပါသည်: {real_error}"}
        except Exception: return {"status": "error", "message": "⚠️ Check Role API Error: အကောင့်စစ်ဆေး၍မရပါ။"}

        query_data = {'user_id': game_id, 'zone_id': zone_id, 'pid': product_id, 'checkrole': '', 'pay_methond': 'smilecoin', 'channel_method': 'smilecoin', '_csrf': csrf_token}
        query_response = scraper.post(query_url, data=query_data, headers=headers)
        
        try: query_result = query_response.json()
        except Exception: return {"status": "error", "message": "Query API Error"}
            
        flowid = query_result.get('flowid') or query_result.get('data', {}).get('flowid')
        
        if not flowid:
            real_error = query_result.get('msg') or query_result.get('message') or ""
            if "login" in str(real_error).lower() or "unauthorized" in str(real_error).lower():
                print("⚠️ Cookie သက်တမ်းကုန်နေပါသည်။ Auto-Login ကို စတင်နေပါသည်...")
                success = auto_login_and_get_cookie()
                if success: return {"status": "error", "message": "⚠️ Session အသစ်ပြန်ယူပြီးပါပြီ။ ကျေးဇူးပြု၍ Command ကို ထပ်မံရိုက်ထည့်ပါ။"}
                else: return {"status": "error", "message": "❌ Auto-Login မအောင်မြင်ပါ။ /setcookie ကို ပြန်ထည့်ပေးပါ။"}
            return {"status": "error", "message": "❌ **အကောင့် မှားယွင်းနေပါသည်:**\nAccount is ban server."}

        pay_data = {'_csrf': csrf_token, 'user_id': game_id, 'zone_id': zone_id, 'pay_methond': 'smilecoin', 'product_id': product_id, 'channel_method': 'smilecoin', 'flowid': flowid, 'email': '', 'coupon_id': ''}
        pay_response = scraper.post(pay_url, data=pay_data, headers=headers)
        pay_text = pay_response.text.lower()
        
        if "saldo insuficiente" in pay_text or "insufficient" in pay_text:
            return {"status": "error", "message": "Main အကောင့်တွင် ငွေအစစ် (Balance) မလုံလောက်ပါ။"}
        
        time.sleep(2) 
        real_order_id = "ရှာမတွေ့ပါ"
        is_success = False

        try:
            hist_res = scraper.get(order_api_url, params={'type': 'orderlist', 'p': '1', 'pageSize': '5'}, headers=headers)
            hist_json = hist_res.json()
            if 'list' in hist_json and len(hist_json['list']) > 0:
                for order in hist_json['list']:
                    if str(order.get('user_id')) == str(game_id) and str(order.get('server_id')) == str(zone_id):
                        if str(order.get('order_status', '')).lower() == 'success' or str(order.get('status')) == '1':
                            real_order_id = str(order.get('increment_id', "ရှာမတွေ့ပါ"))
                            is_success = True
                            break
        except Exception: pass

        if not is_success:
            try:
                pay_json = pay_response.json()
                code = str(pay_json.get('code', ''))
                msg = str(pay_json.get('msg', '')).lower()
                if code in ['200', '0', '1'] or 'success' in msg: is_success = True
            except:
                if 'success' in pay_text or 'sucesso' in pay_text: is_success = True

        if is_success:
            return {"status": "success", "ig_name": ig_name, "order_id": real_order_id}
        else:
            err_msg = "ငွေချေမှု မအောင်မြင်ပါ။"
            try:
                err_json = pay_response.json()
                if 'msg' in err_json: err_msg = f"ငွေချေမှု မအောင်မြင်ပါ။ ({err_json['msg']})"
            except: pass
            return {"status": "error", "message": err_msg}

    except Exception as e: return {"status": "error", "message": f"System Error: {str(e)}"}

# ==========================================
# 4. 🛡️ AUTHORIZATION စစ်ဆေးရန် FUNCTION
# ==========================================
def is_authorized(message):
    if message.from_user.id == OWNER_ID:
        return True
    return db.get_reseller(message.from_user.id) is not None

# ==========================================
# 5. RESELLER MANAGEMENT & COMMANDS
# ==========================================
@bot.message_handler(commands=['addreseller'])
def add_reseller(message):
    if message.from_user.id != OWNER_ID: return bot.reply_to(message, "❌ သင်သည် Owner မဟုတ်ပါ။")
    parts = message.text.split()
    if len(parts) < 2: return bot.reply_to(message, "⚠️ အသုံးပြုရန် ပုံစံ - `/addreseller <user_id>`", parse_mode="Markdown")
        
    target_id = parts[1].strip()
    if not target_id.isdigit(): return bot.reply_to(message, "❌ User ID ကို ဂဏန်းဖြင့်သာ ထည့်ပါ။")
        
    if db.add_reseller(target_id, f"User_{target_id}"):
        bot.reply_to(message, f"✅ Reseller ID `{target_id}` အား V-Wallet ဖြင့် ခွင့်ပြုလိုက်ပါပြီ။", parse_mode="Markdown")
    else:
        bot.reply_to(message, f"⚠️ Reseller ID `{target_id}` သည် စာရင်းထဲတွင် ရှိပြီးသားဖြစ်ပါသည်။", parse_mode="Markdown")

@bot.message_handler(commands=['removereseller'])
def remove_reseller(message):
    if message.from_user.id != OWNER_ID: return bot.reply_to(message, "❌ သင်သည် Owner မဟုတ်ပါ။")
    parts = message.text.split()
    if len(parts) < 2: return bot.reply_to(message, "⚠️ အသုံးပြုရန် ပုံစံ - `/removereseller <user_id>`", parse_mode="Markdown")
        
    target_id = parts[1].strip()
    if target_id == str(OWNER_ID): return bot.reply_to(message, "❌ Owner ကို ပြန်ဖြုတ်၍ မရပါ။")
        
    if db.remove_reseller(target_id):
        bot.reply_to(message, f"✅ Reseller ID `{target_id}` ကို ပိတ်လိုက်ပါပြီ။", parse_mode="Markdown")
    else:
        bot.reply_to(message, "❌ ထို ID သည် စာရင်းထဲတွင် မရှိပါ။")

@bot.message_handler(commands=['resellers'])
def list_resellers(message):
    if message.from_user.id != OWNER_ID: return bot.reply_to(message, "❌ သင်သည် Owner မဟုတ်ပါ။")
    resellers_list = db.get_all_resellers()
    user_list = []
    
    for r in resellers_list:
        role = "owner" if r["tg_id"] == str(OWNER_ID) else "reseller"
        user_list.append(f"🟢 ID: `{r['tg_id']}` ({role})\n   BR: ${r.get('br_balance', 0.0)} | PH: ${r.get('ph_balance', 0.0)}")
            
    final_text = "\n\n".join(user_list) if user_list else "No resellers found."
    bot.reply_to(message, f"🟢 **ခွင့်ပြုထားသော Resellers စာရင်း (V-Wallet):**\n\n{final_text}", parse_mode="Markdown")

@bot.message_handler(commands=['setcookie'])
def set_cookie_command(message):
    if message.from_user.id != OWNER_ID: return bot.reply_to(message, "❌ Owner သာလျှင် Main Cookie ထည့်သွင်းနိုင်ပါသည်။")
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2: return bot.reply_to(message, "⚠️ **အသုံးပြုရန် ပုံစံ:**\n`/setcookie <Main_Cookie_အရှည်ကြီး>`", parse_mode="Markdown")
    
    db.update_main_cookie(parts[1].strip())
    bot.reply_to(message, f"✅ **Main Cookie ကို လုံခြုံစွာ အသစ်ပြောင်းလဲလိုက်ပါပြီ။**", parse_mode="Markdown")

@bot.message_handler(commands=['balance'])
def check_balance_command(message):
    if not is_authorized(message): return bot.reply_to(message, "ɴᴏᴛ ᴀᴜᴛʜᴏʀɪᴢᴇᴅ ᴜsᴇʀ.")
    
    tg_id = str(message.from_user.id)
    user_wallet = db.get_reseller(tg_id)
    if not user_wallet: return bot.reply_to(message, "Yᴏᴜʀ ᴀᴄᴄᴏᴜɴᴛ ɪɴғᴏʀᴍᴀᴛɪᴏɴ ᴄᴀɴɴᴏᴛ ʙᴇ ғᴏᴜɴᴅ.")
    
    report = f"💳 Yᴏᴜʀ ᴠ-ᴡᴀʟʟᴇᴛ ʙᴀʟᴀɴᴄᴇ\n\n"
    report += f"🇧🇷 ʙʀ-ʙᴀʟᴀɴᴄᴇ: ${user_wallet.get('br_balance', 0.0):,.2f}\n"
    report += f"🇵🇭 ᴘʜ-ʙᴀʟᴀɴᴄᴇ: ${user_wallet.get('ph_balance', 0.0):,.2f}"
    
    if message.from_user.id == OWNER_ID:
        loading_msg = bot.reply_to(message, "⏳ Main အကောင့်၏ လက်ကျန်ငွေ အစစ်ကိုပါ ဆွဲယူနေပါသည်...")
        scraper = get_main_scraper()
        headers = {'X-Requested-With': 'XMLHttpRequest', 'Origin': 'https://www.smile.one'}
        try:
            balances = get_smile_balance(scraper, headers, 'https://www.smile.one/customer/order')
            report += f"\n\n💳 **Oғғɪᴄɪᴀʟ ᴀᴄᴄᴏᴜɴᴛ-ʙᴀʟᴀɴᴄᴇ:**\n"
            report += f"ʙʀ-ʙᴀʟᴀɴᴄᴇ: ${balances.get('br_balance', 0.00):,.2f}\n"
            report += f"ᴘʜ-ʙᴀʟᴀɴᴄᴇ: ${balances.get('ph_balance', 0.00):,.2f}"
            bot.edit_message_text(chat_id=message.chat.id, message_id=loading_msg.message_id, text=report, parse_mode="Markdown")
        except:
            bot.edit_message_text(chat_id=message.chat.id, message_id=loading_msg.message_id, text=report)
    else:
        bot.reply_to(message, report)

# ==========================================
# 6. 📌 VIRTUAL WALLET အတွက် ACTIVATION CODE
# ==========================================
@bot.message_handler(func=lambda message: re.match(r"(?i)^/(activecodebr|activecodeph)\b", message.text.strip()))
def handle_activecode(message):
    if not is_authorized(message): return bot.reply_to(message, "ɴᴏᴛ ᴀᴜᴛʜᴏʀɪᴢᴇᴅ ᴜsᴇʀ.")
    
    match = re.search(r"(?i)^/(activecodebr|activecodeph)\s+([a-zA-Z0-9]+)", message.text.strip())
    if not match: return bot.reply_to(message, "⚠️ အသုံးပြုရန် ပုံစံ - `/activecodebr <Code>` သို့မဟုတ် `/activecodeph <Code>`", parse_mode="Markdown")
    
    command_used = match.group(1).lower()
    activation_code = match.group(2).strip()
    tg_id = str(message.from_user.id)
    
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

    loading_msg = bot.reply_to(message, f"📊 {api_type} အတွက် သင့် Wallet သို့ Code `{activation_code}` သွင်းနေပါသည်...", parse_mode="Markdown")
    
    with transaction_lock:
        scraper = get_main_scraper()
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Referer': base_referer,
        }
        
        balance_check_url = 'https://www.smile.one/ph/customer/order' if api_type == 'PH' else 'https://www.smile.one/customer/order'
        old_bal = get_smile_balance(scraper, headers, balance_check_url)

        try:
            res = scraper.get(page_url, headers=headers)
            if "login" in res.url.lower(): return bot.edit_message_text(chat_id=message.chat.id, message_id=loading_msg.message_id, text="ʏᴏᴜʀ ᴄᴏᴏᴋɪᴇs ɪs ᴇxᴘɪʀᴇᴅ.")

            soup = BeautifulSoup(res.text, 'html.parser')
            csrf_token = soup.find('meta', {'name': 'csrf-token'})
            csrf_token = csrf_token.get('content') if csrf_token else (soup.find('input', {'name': '_csrf'}).get('value') if soup.find('input', {'name': '_csrf'}) else None)
            if not csrf_token: return bot.edit_message_text(chat_id=message.chat.id, message_id=loading_msg.message_id, text="❌ CSRF Token မရရှိပါ။")

            ajax_headers = headers.copy()
            ajax_headers.update({'X-Requested-With': 'XMLHttpRequest', 'Origin': base_origin, 'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'})

            check_res = scraper.post(check_url, data={'_csrf': csrf_token, 'pin': activation_code}, headers=ajax_headers).json()
            code_status = str(check_res.get('code', check_res.get('status', '')))
            
            if code_status in ['200', '201', '0', '1'] or 'success' in str(check_res.get('msg', '')).lower():
                bot.edit_message_text(chat_id=message.chat.id, message_id=loading_msg.message_id, text=f"⏳ Code မှန်ကန်ပါသည်။ ငွေသွင်းနေပါသည်...")
                
                pay_res = scraper.post(pay_url, data={'_csrf': csrf_token, 'sec': activation_code}, headers=ajax_headers).json()
                pay_status = str(pay_res.get('code', pay_res.get('status', '')))
                
                if pay_status in ['200', '0', '1'] or 'success' in str(pay_res.get('msg', '')).lower():
                    time.sleep(5) 
                    new_bal = get_smile_balance(scraper, headers, balance_check_url)
                    added_br = round(new_bal['br_balance'] - old_bal['br_balance'], 2)
                    added_ph = round(new_bal['ph_balance'] - old_bal['ph_balance'], 2)
                    
                    currency_msg = "0 (System Delay)"
                    if api_type == 'BR' and added_br > 0:
                        db.update_balance(tg_id, br_amount=added_br)
                        currency_msg = f"{added_br} BR"
                    elif api_type == 'PH' and added_ph > 0:
                        db.update_balance(tg_id, ph_amount=added_ph)
                        currency_msg = f"{added_ph} PH"

                    bot.edit_message_text(chat_id=message.chat.id, message_id=loading_msg.message_id, text=f"sᴍɪʟᴇ ᴏɴᴇ ʀᴇᴅᴇᴇᴍ ᴄᴏᴅᴇ sᴜᴄᴄᴇss ✅")
                else:
                    bot.edit_message_text(chat_id=message.chat.id, message_id=loading_msg.message_id, text=f"Rᴇᴅᴇᴇᴍ Fᴀɪʟ ❌")
            else:
                bot.edit_message_text(chat_id=message.chat.id, message_id=loading_msg.message_id, text=f"Cʜᴇᴄᴋ Fᴀɪʟᴇᴅ❌")

        except Exception as e:
            bot.edit_message_text(chat_id=message.chat.id, message_id=loading_msg.message_id, text=f"❌ Error: {str(e)}")

# ==========================================
# 7. 📌 ROLE စစ်ဆေးရန် COMMAND
# ==========================================
@bot.message_handler(func=lambda message: re.match(r"(?i)^/?role\b", message.text.strip()))
def handle_check_role(message):
    if not is_authorized(message):
        return bot.reply_to(message, "ɴᴏᴛ ᴀᴜᴛʜᴏʀɪᴢᴇᴅ ᴜsᴇʀ.", parse_mode="Markdown")

    match = re.search(r"(?i)^/?role\s+(\d+)\s*\(\s*(\d+)\s*\)", message.text.strip())
    if not match:
        return bot.reply_to(message, "❌ Format မှားယွင်းနေပါသည်:\n(ဥပမာ - `/role 123456789 (12345)`)", parse_mode="Markdown")

    game_id = match.group(1).strip()
    zone_id = match.group(2).strip()
    
    loading_msg = bot.reply_to(message, "💻")

    scraper = get_main_scraper()
    
    main_url = 'https://www.smile.one/merchant/mobilelegends'
    checkrole_url = 'https://www.smile.one/merchant/mobilelegends/checkrole'
    headers = {'X-Requested-With': 'XMLHttpRequest', 'Referer': main_url, 'Origin': 'https://www.smile.one'}

    try:
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

        check_data = {'user_id': game_id, 'zone_id': zone_id, '_csrf': csrf_token}
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

        pizzo_region = "Unknown"
        try:
            pizzo_headers = {
                'authority': 'pizzoshop.com',
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'content-type': 'application/x-www-form-urlencoded',
                'origin': 'https://pizzoshop.com',
                'referer': 'https://pizzoshop.com/mlchecker',
                'user-agent': 'Mozilla/5.0'
            }
            scraper.get("https://pizzoshop.com/mlchecker", headers=pizzo_headers, timeout=10)
            pizzo_res = scraper.post("https://pizzoshop.com/mlchecker/check", data={'user_id': game_id, 'zone_id': zone_id}, headers=pizzo_headers, timeout=15)
            pizzo_soup = BeautifulSoup(pizzo_res.text, 'html.parser')
            table = pizzo_soup.find('table', class_='table-modern')
            
            if table:
                for row in table.find_all('tr'):
                    th, td = row.find('th'), row.find('td')
                    if th and td and ('region id' in th.get_text(strip=True).lower() or 'region' in th.get_text(strip=True).lower()):
                        pizzo_region = td.get_text(strip=True)
        except: pass

        final_region = pizzo_region if pizzo_region != "Unknown" else smile_region

        report = f"ɢᴀᴍᴇ ɪᴅ : {game_id} ({zone_id})\nɪɢɴ ɴᴀᴍᴇ : {ig_name}\nʀᴇɢɪᴏɴ : {final_region}"
        bot.edit_message_text(chat_id=message.chat.id, message_id=loading_msg.message_id, text=report)

    except Exception as e:
        bot.edit_message_text(chat_id=message.chat.id, message_id=loading_msg.message_id, text=f"❌ System Error: {str(e)}")

# ==========================================
# 8. 💎 V-WALLET ဖြင့် ဝယ်ယူခြင်း (COMMAND HANDLER)
# ==========================================
@bot.message_handler(func=lambda message: re.match(r"(?i)^(br|bro|ph|pho)\s+\d+", message.text.strip()))
def handle_direct_buy(message):
    if not is_authorized(message):
        return bot.reply_to(message, f"ɴᴏᴛ ᴀᴜᴛʜᴏʀɪᴢᴇᴅ ᴜsᴇʀ.", parse_mode="Markdown")

    try:
        tg_id = str(message.from_user.id)
        lines = message.text.strip().split('\n')
        
        # Telegram နာမည်အစစ်ကို ယူမည်
        first_name = message.from_user.first_name or ""
        last_name = message.from_user.last_name or ""
        full_name = f"{first_name} {last_name}".strip()
        if not full_name:
            full_name = "User"
            
        safe_full_name = full_name.replace('<', '').replace('>', '')
        username_display = f'<a href="tg://user?id={tg_id}">{safe_full_name}</a>'
        
        with transaction_lock:
            for line in lines:
                line = line.strip()
                if not line: continue 
                    
                match = re.search(r"(?i)^(br|bro|ph|pho)\s*(\d+)\s*\(\s*(\d+)\s*\)\s*([a-zA-Z0-9]+)", line)
                if not match:
                    bot.reply_to(message, f"❌ Format မှားယွင်းနေပါသည်: `{line}`\n(ဥပမာ - br 12345678 (1234) wp)", parse_mode="Markdown")
                    continue
                    
                cmd_px, game_id, zone_id, item_input = match.group(1).lower(), match.group(2), match.group(3), match.group(4).lower()
                
                currency_name = 'PH' if cmd_px in ['ph', 'pho'] else 'BR'
                active_pkgs = PH_PACKAGES if currency_name == 'PH' else BR_PACKAGES
                v_bal_key = 'ph_balance' if currency_name == 'PH' else 'br_balance'
                
                if item_input not in active_pkgs:
                    bot.reply_to(message, f"❌ '{item_input}' အတွက် Package မရှိပါ။")
                    continue
                    
                items_to_buy = active_pkgs[item_input]
                total_required_price = sum(item['price'] for item in items_to_buy)
                
                user_wallet = db.get_reseller(tg_id)
                user_v_bal = user_wallet.get(v_bal_key, 0.0) if user_wallet else 0.0
                
                if user_v_bal < total_required_price:
                    error_text = (
                        f"Nᴏᴛ ᴇɴᴏᴜɢʜ ᴍᴏɴᴇʏ ɪɴ ʏᴏᴜʀ ᴠ-ᴡᴀʟʟᴇᴛ.\n"
                        f"Nᴇᴇᴅ ʙᴀʟᴀɴᴄᴇ ᴀᴍᴏᴜɴᴛ: {total_required_price} {currency_name}\n"
                        f"Yᴏᴜʀ ʙᴀʟᴀɴᴄᴇ: {user_v_bal} {currency_name}"
                    )
                    bot.reply_to(message, error_text, parse_mode="Markdown")
                    continue
                
                loading_msg = bot.reply_to(message, f"💻", parse_mode="Markdown")
                
                success_count = 0
                fail_count = 0
                total_spent = 0.0
                order_ids_str = ""
                ig_name = "Unknown"
                error_msg = ""
                first_order = True
                
                for item in items_to_buy:
                    result = process_smile_one_order(game_id, zone_id, item['pid'], currency_name)
                    
                    if result['status'] == 'success':
                        if first_order:
                            ig_name = result['ig_name']
                            first_order = False
                        
                        success_count += 1
                        total_spent += item['price']
                        
                        order_ids_str += f"{result['order_id']}\n"
                        
                        time.sleep(random.randint(5, 10)) 
                    else:
                        fail_count += 1
                        error_msg = result['message']
                        break 
                
                if success_count > 0:
                    now = datetime.datetime.now(MMT)
                    date_str = now.strftime("%m/%d/%Y, %I:%M:%S %p")
                    
                    if currency_name == 'BR':
                        db.update_balance(tg_id, br_amount=-total_spent)
                    else:
                        db.update_balance(tg_id, ph_amount=-total_spent)
                    
                    new_wallet = db.get_reseller(tg_id)
                    new_v_bal = new_wallet.get(v_bal_key, 0.0) if new_wallet else 0.0
                    
                    safe_ig_name = str(ig_name).replace('<', '&lt;').replace('>', '&gt;')

                    report = f"<b>{cmd_px.upper()} {game_id} ({zone_id}) {item_input}</b>\n"
                    report += "=== ᴛʀᴀɴsᴀᴄᴛɪᴏɴ ʀᴇᴘᴏʀᴛ ===\n\n"
                    report += "ᴏʀᴅᴇʀ sᴛᴀᴛᴜs: ✅ Sᴜᴄᴄᴇss\n"
                    report += f"ɢᴀᴍᴇ ɪᴅ: {game_id} {zone_id}\n"
                    report += f"ɪɢ ɴᴀᴍᴇ: {safe_ig_name}\n"
                    report += f"ᴏʀᴅᴇʀ ɪᴅ:\n`{order_ids_str}`"
                    report += f"ɪᴛᴇᴍ: {item_input} 💎\n"
                    report += f"ᴛᴏᴛᴀʟ ᴀᴍᴏᴜɴᴛ: {total_spent:.2f} 🪙\n\n"
                    report += f"ᴅᴀᴛᴇ: {date_str}\n"
                    report += f"ᴜsᴇʀɴᴀᴍᴇ: {username_display}\n"
                    report += f"ᴛᴏᴛᴀʟ sᴘᴇɴᴛ: ${total_spent:.2f}\n"
                    report += f"ɪɴɪᴛɪᴀʟ ʙᴀʟᴀɴᴄᴇ: ${user_v_bal:.2f}\n"
                    report += f"ғɪɴᴀʟ ʙᴀʟᴀɴᴄᴇ: ${new_v_bal:.2f}\n\n"
                    report += f"Sᴜᴄᴄᴇss {success_count} / Fᴀɪʟ {fail_count}" 

                    # ✅ Username Link အလုပ်လုပ်ရန် parse_mode="HTML" ထည့်ပေးထားပါသည်
                    bot.edit_message_text(chat_id=message.chat.id, message_id=loading_msg.message_id, text=report, parse_mode="Markdown")
                    if fail_count > 0: bot.reply_to(message, f"⚠️ အချို့သာ အောင်မြင်ပါသည်။\nError: {error_msg}")
                else:
                    # ✅ Duplicate else ကိုဖျက်ပြီး သင်လိုချင်သော Error စာသားဖြင့် အစားထိုးထားပါသည်
                    bot.edit_message_text(chat_id=message.chat.id, message_id=loading_msg.message_id, text=f"Oʀᴅᴇʀ ғᴀɪʟ❌\n{error_msg}")

    except Exception as e:
        bot.reply_to(message, f"Sʏsᴛᴇᴍ ᴇʀʀᴏʀ: {str(e)}")


# ==========================================
# 10. 💓 HEARTBEAT FUNCTION
# ==========================================
def keep_cookie_alive():
    while True:
        try:
            time.sleep(10 * 60) 
            scraper = get_main_scraper()
            headers = {
                'User-Agent': 'Mozilla/5.0',
                'X-Requested-With': 'XMLHttpRequest',
                'Origin': 'https://www.smile.one'
            }
            response = scraper.get('https://www.smile.one/customer/order', headers=headers)
            if "login" not in response.url.lower() and response.status_code == 200:
                print(f"[{datetime.datetime.now(MMT).strftime('%I:%M %p')}] 💓 Main Cookie is alive!")
            else:
                print(f"[{datetime.datetime.now(MMT).strftime('%I:%M %p')}] ⚠️ Main Cookie expired. Auto-login triggered.")
                auto_login_and_get_cookie()
        except: pass

# ==========================================
# 9. START BOT / DEFAULT COMMAND
# ==========================================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    try:
        tg_id = str(message.from_user.id)
        
        # Telegram နာမည်အစစ်ကို ယူမည်
        first_name = message.from_user.first_name or ""
        last_name = message.from_user.last_name or ""
        full_name = f"{first_name} {last_name}".strip()
        if not full_name:
            full_name = "User"
            
        # နာမည်ကို နှိပ်လျှင် Profile သို့ရောက်မည့် HTML Link (HTML Error မတက်စေရန် < > များ ဖယ်မည်)
        safe_full_name = full_name.replace('<', '').replace('>', '')
        username_display = f'<a href="tg://user?id={tg_id}">{safe_full_name}</a>'
        
        if is_authorized(message):
            status = "🟢 Aᴄᴛɪᴠᴇ"
        else:
            status = "🔴 Nᴏᴛ Aᴄᴛɪᴠᴇ"
            
        welcome_text = (
            f"ʜᴇʏ ʙᴀʙʏ🥺\n\n"
            f"Usᴇʀɴᴀᴍᴇ: {username_display}\n"
            f"𝐈𝐃: `{tg_id}`\n"
            f"Sᴛᴀᴛᴜs: {status}\n\n"
            f"Cᴏɴᴛᴀᴄᴛ ᴜs: @iwillgoforwardsalone"
        )
        bot.reply_to(message, welcome_text, parse_mode="Markdown")

# ==========================================
# 10. RUN BOT
# ==========================================
if __name__ == '__main__':
    print("Clearing old webhooks if any...")
    try:
        bot.remove_webhook()
        time.sleep(1)
    except: pass
        
    print("Starting Heartbeat & Auto-login thread...")
    threading.Thread(target=keep_cookie_alive, daemon=True).start()

    print("Bot is successfully running (With MongoDB Virtual Wallet System)...")
    bot.infinity_polling()
