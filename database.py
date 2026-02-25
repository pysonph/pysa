import os
import datetime
from pymongo import MongoClient
from dotenv import load_dotenv

# ==========================================
# 📌 SETUP & CONNECTION
# ==========================================
load_dotenv()
MONGO_URI = os.getenv('MONGO_URI')

if not MONGO_URI:
    print("❌ Error: .env ဖိုင်ထဲတွင် MONGO_URI မပါဝင်ပါ။")
    exit()

try:
    # Timeout နှင့် Connection Pool များကို ပိုမိုကောင်းမွန်အောင် သတ်မှတ်ထားသည်
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client['smile_vwallet_db']
    
    resellers_col = db['resellers']
    settings_col = db['settings']
    orders_col = db['orders']
    
    print("✅ MongoDB ချိတ်ဆက်မှု အောင်မြင်ပါသည်။ (Virtual Wallet Database)")
except Exception as e:
    print(f"❌ MongoDB ချိတ်ဆက်မှု မအောင်မြင်ပါ: {e}")
    exit()

# မြန်မာစံတော်ချိန် (MMT) ကို Global အနေဖြင့် သတ်မှတ်ထားသည်
MMT = datetime.timezone(datetime.timedelta(hours=6, minutes=30))

# ==========================================
# 🚀 DATABASE INDEXING (For Speed Optimization)
# ==========================================
def setup_indexes():
    """ဒေတာများလာသည့်အခါ ရှာဖွေမှုမြန်ဆန်စေရန် Index များ တည်ဆောက်မည်"""
    try:
        resellers_col.create_index("tg_id", unique=True)
        # Order History ဆွဲထုတ်ရာတွင် မြန်ဆန်စေရန် tg_id နှင့် timestamp ကို ပေါင်း၍ Index လုပ်ထားသည်
        orders_col.create_index([("tg_id", 1), ("timestamp", -1)])
    except Exception as e:
        print(f"⚠️ Index ဖန်တီးရာတွင် အမှားရှိပါသည်: {e}")

# Script run သည်နှင့် Index များကို စစ်ဆေး/တည်ဆောက်မည်
setup_indexes()

# ==========================================
# 👑 OWNER & COOKIE MANAGEMENT
# ==========================================
def init_owner(owner_id):
    """Bot စတင်ချိန်တွင် Owner အား Default ထည့်သွင်းပေးမည်"""
    owner_str = str(owner_id)
    if not resellers_col.find_one({"tg_id": owner_str}):
        resellers_col.insert_one({
            "tg_id": owner_str,
            "username": "Owner",
            "br_balance": 0.0,
            "ph_balance": 0.0
        })

def get_main_cookie():
    """Main Cookie အား Database မှ ယူမည်"""
    doc = settings_col.find_one({"type": "main_cookie"})
    return doc.get("cookie", "") if doc else ""

def update_main_cookie(cookie_str):
    """Main Cookie အား Database သို့ သိမ်းမည်"""
    settings_col.update_one(
        {"type": "main_cookie"},
        {"$set": {"cookie": cookie_str}},
        upsert=True
    )

# ==========================================
# 👥 RESELLER (V-WALLET) MANAGEMENT
# ==========================================
def get_reseller(tg_id):
    """Reseller တစ်ဦးချင်းစီ၏ အချက်အလက်များကို ယူမည်"""
    return resellers_col.find_one({"tg_id": str(tg_id)})

def get_all_resellers():
    """Reseller အားလုံး၏ စာရင်းကို ယူမည်"""
    return list(resellers_col.find({}))

def add_reseller(tg_id, username):
    """Reseller အသစ်ထည့်မည်"""
    tg_id_str = str(tg_id)
    if not resellers_col.find_one({"tg_id": tg_id_str}):
        resellers_col.insert_one({
            "tg_id": tg_id_str,
            "username": username,
            "br_balance": 0.0,
            "ph_balance": 0.0
        })
        return True
    return False

def remove_reseller(tg_id):
    """Reseller အား စာရင်းမှ ဖျက်မည်"""
    result = resellers_col.delete_one({"tg_id": str(tg_id)})
    return result.deleted_count > 0

def update_balance(tg_id, br_amount=0.0, ph_amount=0.0):
    """
    Reseller ၏ Balance အား အတိုး/အလျော့ လုပ်မည်။
    Float Precision Error (ဥပမာ 0.300000000004) မဖြစ်စေရန် round() သုံးထားပါသည်။
    """
    resellers_col.update_one(
        {"tg_id": str(tg_id)},
        {"$inc": {
            "br_balance": round(float(br_amount), 2), 
            "ph_balance": round(float(ph_amount), 2)
        }}
    )

# ==========================================
# 📜 ORDER HISTORY MANAGEMENT
# ==========================================
def save_order(tg_id, game_id, zone_id, item_name, price, order_id, status="success"):
    """Order အောင်မြင်ပါက Database သို့ မှတ်တမ်းတင်မည်"""
    now = datetime.datetime.now(MMT)
    
    order_data = {
        "tg_id": str(tg_id),
        "game_id": str(game_id),
        "zone_id": str(zone_id),
        "item_name": item_name,
        "price": round(float(price), 2),
        "order_id": str(order_id),
        "status": status,
        "date_str": now.strftime("%I:%M:%S %p %d.%m.%Y"), 
        "timestamp": now 
    }
    orders_col.insert_one(order_data)

def get_user_history(tg_id, limit=5):
    """User တစ်ယောက်၏ နောက်ဆုံး Order များကို ဆွဲထုတ်မည်"""
    cursor = orders_col.find(
        {"tg_id": str(tg_id)}, 
        {"_id": 0} # _id (ObjectId) ကို ဖျောက်ထားမည်
    ).sort("timestamp", -1).limit(limit)
    
    return list(cursor)
