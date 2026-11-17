import os
import threading
from flask import Flask
from robka import Robot
from robka.context import Message
from robka.button import InlineBuilder

# --- تنظیمات ---
# ⚠️ اینجا رو حتماً با توکن ربات خودت جایگزین کن
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE" 
ADMIN_ID = "b0DmuXe01mL02f80dd47960a7bbf297d"

# --- وب‌سرور Flask ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

@app.route('/health')
def health():
    return "OK", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- کد اصلی ربات ---
bot = Robot(token=BOT_TOKEN)

MENU_OPTIONS = {
    "service_1": "1️⃣ ساخت فارم",
    "service_2": "2️⃣ خرید کارت طلایی",
    "service_3": "3️⃣ انجام ماموریت کاپیتانی",
    "service_4": "4️⃣ انجام رویداد ها",
    "service_5": "5️⃣ خرید منابع",
    "service_6": "6️⃣ غیره"
}
user_states = {}

@bot.on_message(commands=["start", "shop"])
def start_handler(bot: Robot, message: Message):
    chat_id = message.chat_id
    user_states[chat_id] = {"step": "main_menu", "data": {}}
    
    welcome_text = (
        "سلام خوش اومدی! 👋\n"
        "من ربات خدمات و فروشگاه هستم.\n"
        "لطفاً روی دکمه مربوط به کاری که می‌خوای انجام بدیم بزن:"
    )
    
    builder = InlineBuilder()
    for key, value in MENU_OPTIONS.items():
        builder.row(builder.button_simple(id=key, text=value))
        
    message.reply(welcome_text, inline_keypad=builder.build())

@bot.on_callback()
def handle_callbacks(bot: Robot, message: Message):
    chat_id = message.chat_id
    
    # 🐞 این خطوط برای پیدا کردن مشکل دکمه‌هاست (توی لاگ رندر چاپ میشه)
    print(f"=== دکمه زده شد! ===")
    print(f"Chat ID: {chat_id}")
    print(f"Data: {getattr(message, 'data', None)}")
    print(f"Aux Data: {getattr(message, 'aux_data', None)}")
    print(f"=====================")

    # تلاش برای گرفتن دیتای دکمه از هر دو متغیر ممکن (برای رفع باگ کتابخانه)
    data = getattr(message, "data", None) or getattr(message, "aux_data", None)
    
    if not data:
        return

    # --- بخش تایید و رد ادمین ---
    if str(chat_id) == str(ADMIN_ID) and (data.startswith("approve_") or data.startswith("reject_")):
        if data.startswith("approve_"):
            uid = data.replace("approve_", "")
            try:
                bot.send_message(chat_id=uid, text="🎉 سفارش شما توسط مدیر **تأیید شد**!\nبه‌زودی برای هماهنگی بیشتر با شما تماس گرفته می‌شه.")
            except:
                pass
            message.reply(f"سفارش {uid} **تأیید** شد.")
            
        elif data.startswith("reject_"):
            uid = data.replace("reject_", "")
            try:
                bot.send_message(chat_id=uid, text="😔 متأسفانه سفارش شما توسط مدیر **رد شد**.\nاگه سوالی داری می‌تونی دوباره تلاش کنی.")
            except:
                pass
            message.reply(f"سفارش {uid} **رد** شد.")
        return

    # --- بخش انتخاب منو توسط کاربر ---
    if chat_id in user_states and user_states[chat_id]["step"] == "main_menu":
        if data in MENU_OPTIONS:
            chosen_service = MENU_OPTIONS[data]
            clean_service_name = chosen_service.split(" ", 1)[-1] 
            
            user_states[chat_id]["data"]["service"] = clean_service_name
            user_states[chat_id]["step"] = "waiting_details"
            
            message.reply(
                f"شما گزینه **{clean_service_name}** را انتخاب کردید. ✅\n\n"
                f"لطفاً حالا **نام سرور** یا **آیدی بازیتون** رو همراه با توضیحات (مثلاً تعداد) بفرستید:"
            )

@bot.on_message()
def handle_messages(bot: Robot, message: Message):
    chat_id = message.chat_id
    text = (message.text or "").strip()

    if chat_id not in user_states:
        start_handler(bot, message)
        return

    state = user_states[chat_id]

    if state["step"] == "waiting_details":
        state["data"]["details"] = text
        state["step"] = "pending_admin"

        order_text = (
            f"📦 **سفارش جدید**\n"
            f"👤 کاربر: {chat_id}\n"
            f"🛠 خدمت: {state['data']['service']}\n"
            f"📝 جزئیات (سرور/تعداد): {text}\n\n"
            f"منتظر تایید شما هستم..."
        )

        builder = InlineBuilder()
        builder.row(
            builder.button_simple(id=f"approve_{chat_id}", text="✅ تایید سفارش"),
            builder.button_simple(id=f"reject_{chat_id}", text="❌ رد سفارش")
        )

        try:
            bot.send_message(chat_id=ADMIN_ID, text=order_text, inline_keypad=builder.build())
            message.reply("✅ سفارش شما ثبت شد و برای بررسی به مدیر ارسال شد.\nمنتظر بمون تا تایید بشه...")
        except Exception as e:
            message.reply("⚠️ مشکلی در ارسال سفارش پیش آمد. لطفاً دوباره تلاش کنید.")
            print(f"Error sending to admin: {e}")
        
        del user_states[chat_id]

# --- اجرای همزمان وب‌سرور و ربات ---
if __name__ == "__main__":
    print("🤖 ربات و وب‌سرور فعال شدند...")
    threading.Thread(target=run_flask, daemon=True).start()
    bot.run()
