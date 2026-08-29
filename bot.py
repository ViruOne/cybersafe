"""
👑 LAZZAT — Rasmiy Telegram Autentifikatsiya Boti
==================================================
Talablar:
1. Faqat O'zbekiston (+998...) raqamlarini qabul qiladi.
2. Qo'lda yozilgan raqamlar qabul qilinmaydi (faqat Telegram "Share Contact" tugmasi orqali).
3. Yuborilgan tasdiqlash kodining amal qilish muddati roppa-rosa 2 daqiqa (120 soniya).
"""

import asyncio
import logging
import os
import random
from datetime import datetime, timedelta, timezone

from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from dotenv import load_dotenv

# .env faylini yuklash
load_dotenv()

# Konfiguratsiya — turli nomdagi o'zgaruvchilarni qabul qilish va bo'shliqlarni tozalash
BOT_TOKEN = (
    os.getenv("BOT_TOKEN")
    or os.getenv("TELEGRAM_BOT_TOKEN")
    or os.getenv("TOKEN")
    or "8654252494:AAGV1gvGEBNXhPWck1Zkm4Y-9cGM4npLN4o"
).strip().strip('"').strip("'")

# Agar kiritilgan token noto'g'ri bo'lsa yoki ikki nuqta bo'lmasa, avtomatik haqiqiy tokenni ishlatish
if not BOT_TOKEN or ":" not in BOT_TOKEN or BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
    BOT_TOKEN = "8654252494:AAGV1gvGEBNXhPWck1Zkm4Y-9cGM4npLN4o"

# Supabase URL va Key ni xavfsiz tozalash
_raw_url = (
    os.getenv("SUPABASE_URL")
    or os.getenv("SUPABASE_PROJECT_URL")
    or "https://pppkorhqrrsgmfkonalb.supabase.co"
).strip().strip('"').strip("'").rstrip("/")

if _raw_url and not _raw_url.startswith("http://") and not _raw_url.startswith("https://"):
    _raw_url = f"https://{_raw_url}"

SUPABASE_URL = _raw_url if _raw_url else "https://pppkorhqrrsgmfkonalb.supabase.co"

SUPABASE_KEY = (
    os.getenv("SUPABASE_KEY")
    or os.getenv("SUPABASE_ANON_KEY")
    or "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBwcGtvcmhxcnJzZ21ma29uYWxiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODc4MjUxNjIsImV4cCI6MjEwMzQwMTE2Mn0.agWcjMS1tIdDmmPvyRNXFMo3zbN8lJQYg7i_PW4RsAM"
).strip().strip('"').strip("'")

import sys

# Logging sozlamalari
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

logger.info(f"🔑 Telegram Bot Token faollashtirildi (Uzunligi: {len(BOT_TOKEN)} belgi)")

# Bot va Dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Xotiradagi OTP saqlash joyi (In-Memory Fallback)
otp_storage: dict[str, dict] = {}
pending_auth_phones: dict[int, str] = {}

# Rate Limiting Konfiguratsiyasi (Flood & Spam Himoyasi)
otp_request_timestamps: dict[str, list[datetime]] = {}
RATE_LIMIT_COOLDOWN_SECONDS = 60  # Bitta raqamdan qayta so'rov orasidagi tanaffus (60 soniya)
RATE_LIMIT_MAX_PER_HOUR = 5  # 1 soatda maksimal 5 ta OTP kodi


def normalize_phone(raw: str) -> str:
    """Telefon raqamni standart 12 xonali formatga (998901234567) keltiradi"""
    digits = "".join([c for c in str(raw) if c.isdigit()])
    if digits.startswith("998") and len(digits) == 12:
        return digits
    if len(digits) == 9:
        return f"998{digits}"
    if digits.startswith("8") and len(digits) == 10:
        return f"998{digits[1:]}"
    return digits


def check_rate_limit(phone: str, user_id: int) -> tuple[bool, str]:
    """
    Telefon raqami va Telegram User ID bo'yicha so'rovlar chastotasini tekshiradi.
    Qaytaradi: (ruxsat_berildimi: bool, rad_etish_sababi_html: str)
    """
    now = datetime.now(timezone.utc)
    keys_to_check = [f"phone_{phone}", f"user_{user_id}"]

    for key in keys_to_check:
        history = otp_request_timestamps.get(key, [])
        # 1 soatdan eski vaqtlarni tozalash
        history = [t for t in history if (now - t).total_seconds() < 3600]
        otp_request_timestamps[key] = history

        # 1. Soatlik cheklov (Maksimal 5 ta)
        if len(history) >= RATE_LIMIT_MAX_PER_HOUR:
            oldest = history[0]
            cooldown_rem = int(3600 - (now - oldest).total_seconds())
            mins_rem = max(1, cooldown_rem // 60)
            return (
                False,
                f"🚫 <b>Xavfsizlik cheklovi faollashdi!</b>\n\n"
                f"Siz 1 soatlik maksimal limitdan (<b>{RATE_LIMIT_MAX_PER_HOUR} ta OTP</b>) oshib ketdingiz.\n\n"
                f"⏳ Iltimos, <b>{mins_rem} daqiqa</b>dan so'ng qayta urinib ko'ring.",
            )

        # 2. Qisqa muddatli so'rovlar orasidagi tanaffus (60 soniya)
        if history:
            last_request = history[-1]
            elapsed = (now - last_request).total_seconds()
            if elapsed < RATE_LIMIT_COOLDOWN_SECONDS:
                remaining_sec = int(RATE_LIMIT_COOLDOWN_SECONDS - elapsed)
                return (
                    False,
                    f"⏳ <b>Iltimos, biroz kuting!</b>\n\n"
                    f"Xavfsizlik yuzasidan yangi tasdiqlash kodini olish uchun yana <b>{remaining_sec} soniya</b> kuting.\n\n"
                    f"<i>Eslatma: Avval yuborilgan kod 2 daqiqa davomida amal qiladi.</i>",
                )

    return (True, "")


def record_successful_otp_request(phone: str, user_id: int):
    """Muvaffaqiyatli OTP so'rovining vaqtini tarixga qayd etadi"""
    now = datetime.now(timezone.utc)
    for key in [f"phone_{phone}", f"user_{user_id}"]:
        if key not in otp_request_timestamps:
            otp_request_timestamps[key] = []
        otp_request_timestamps[key].append(now)


# ==============================================================================
# 1. /start BUYRUG'I
# ==============================================================================
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    """
    Foydalanuvchi botga kirganda yoki ilovadan kelganda ishga tushadi.
    Faqat 'Telefon raqamni yuborish' tugmasini chiqaradi.
    """
    user = message.from_user
    first_name = user.first_name if user else "Foydalanuvchi"
    user_id = user.id if user else 0

    # Start argumentidan ilovada kiritilgan telefon raqamini olish (masalan: /start reg_998901234567)
    command_text = message.text or ""
    if "reg_" in command_text:
        extracted_phone = normalize_phone(command_text.split("reg_")[-1])
        if extracted_phone.startswith("998") and len(extracted_phone) == 12:
            pending_auth_phones[user_id] = extracted_phone

    # Maxsus kontakt so'rash tugmasi (Qo'lda kiritishni oldini olish uchun)
    contact_keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="📱 Telefon raqamni yuborish",
                    request_contact=True,
                )
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

    caption = (
        f"👑 <b>Assalomu alaykum, {first_name}!</b>\n\n"
        f"<b>«LAZZAT»</b> — mazali taomlar yetkazib berish ilovasining rasmiy "
        f"autentifikatsiya botiga xush kelibsiz! 🍽️✨\n\n"
        f"📲 Ilovaga xavfsiz ro'yxatdan o'tish yoki kirish uchun, iltimos, "
        f"pastdagi <b>«📱 Telefon raqamni yuborish»</b> tugmasini bosing.\n\n"
        f"<i>⚠️ Eslatma: Xavfsizlik yuzasidan ilovada kiritilgan raqam bilan Telegram "
        f"hisobingizdagi raqam aynan bir xil bo'lishi shart.</i>"
    )

    await message.answer(
        caption,
        parse_mode=ParseMode.HTML,
        reply_markup=contact_keyboard,
    )


# ==============================================================================
# 2. KONTAKT QABUL QILISH (FAQAT HAQIQIY TELEGRAM KONTAKTI)
# ==============================================================================
@dp.message(F.contact)
async def handle_contact(message: types.Message):
    """
    Foydalanuvchi 'request_contact' orqali kontakt yuborganida ishlaydi.
    """
    contact = message.contact
    user_id = message.from_user.id if message.from_user else 0

    # 1-Tekshiruv: Kontakt aynan ushbu foydalanuvchining o'zinikimi? (Boshqa odam kontaktini forward qilmaslik)
    if contact.user_id and contact.user_id != user_id:
        await message.answer(
            "❌ <b>Xatolik!</b>\n\n"
            "Siz boshqa foydalanuvchining kontaktini yubordingiz. "
            "Iltimos, faqat o'zingizning Telegram hisobingizga biriktirilgan raqamni yuboring.",
            parse_mode=ParseMode.HTML,
        )
        return

    # Telefon raqamini tozalash va standartlashtirish
    raw_phone = normalize_phone(contact.phone_number)

    # 2-Tekshiruv: Faqat O'zbekiston raqami (+998...) bo'lishi shart!
    if not (raw_phone.startswith("998") and len(raw_phone) == 12):
        await message.answer(
            f"❌ <b>Kechirasiz!</b>\n\n"
            f"<b>«LAZZAT»</b> ilovasi hozircha faqat <b>O'zbekiston telefon raqamlari (+998...)</b> "
            f"uchun xizmat ko'rsatadi.\n\n"
            f"Sizning raqamingiz: <code>+{raw_phone}</code>\n"
            f"Iltimos, O'zbekiston raqamiga ochilgan Telegram orqali kiring.",
            parse_mode=ParseMode.HTML,
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    # 3-Tekshiruv: Ilovada kiritilgan telefon raqam bilan Telegramdagi raqam bir xilmi?
    expected_phone = pending_auth_phones.get(user_id)
    if expected_phone and expected_phone != raw_phone:
        await message.answer(
            f"❌ <b>Telefon raqamlar mos kelmadi!</b>\n\n"
            f"📱 Ilovada kiritilgan raqam: <code>+{expected_phone}</code>\n"
            f"👤 Telegramdagi raqamingiz: <code>+{raw_phone}</code>\n\n"
            f"Iltimos, ilovada o'zingizning <b>Telegram hisobingizga tegishli raqamni</b> kiriting va qaytadan urinib ko'ring.",
            parse_mode=ParseMode.HTML,
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    # 4-Tekshiruv: Rate Limiting (Flood & Spam Himoyasi — 60s cooldown & 5 max/soat)
    is_allowed, rate_limit_msg = check_rate_limit(raw_phone, user_id)
    if not is_allowed:
        await message.answer(
            rate_limit_msg,
            parse_mode=ParseMode.HTML,
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    # Muvaffaqiyatli urinish vaqtini qayd etish
    record_successful_otp_request(raw_phone, user_id)

    # 5-Qadam: 6 xonali xavfsiz OTP kod generatsiya qilish
    otp_code = f"{random.randint(100000, 999999)}"
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=2)  # 2 daqiqalik amal qilish muddati

    # Xotiraga saqlash
    otp_storage[raw_phone] = {
        "code": otp_code,
        "expires_at": expires_at,
        "user_id": user_id,
        "username": message.from_user.username if message.from_user else "",
    }

    # Supabase bazasiga saqlash
    await save_otp_to_supabase(raw_phone, user_id, message.from_user.username or "", otp_code, expires_at)

    logger.info(f"✅ OTP generated for +{raw_phone}: {otp_code} (Expires in 2 mins)")

    # 4-Qadam: Foydalanuvchiga chiroyli tasdiqlash xabari yuborish
    formatted_phone = f"+{raw_phone[:3]} ({raw_phone[3:5]}) {raw_phone[5:8]}-{raw_phone[8:10]}-{raw_phone[10:12]}"

    response_text = (
        f"👑 <b>«LAZZAT» ILovasi — Tasdiqlash Kodi</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📱 Telefon raqam: <b>{formatted_phone}</b>\n\n"
        f"🔐 Sizning bir martalik kodingiz:\n"
        f"👉 <code>{otp_code}</code> 👈 <i>(nusxalash uchun ustiga bosing)</i>\n\n"
        f"⏳ <b>Kodning amal qilish muddati:</b> 2 daqiqa (120 soniya)\n"
        f"⚠️ <i>Xavfsizlik eslatmasi: Ushbu kodni hech kimga, hatto ilova xodimlariga ham bermang!</i>\n"
        f"━━━━━━━━━━━━━━━━━━━━━"
    )

    await message.answer(
        response_text,
        parse_mode=ParseMode.HTML,
        reply_markup=ReplyKeyboardRemove(),
    )


# ==============================================================================
# 3. QO'LDA MATN / RAQAM KIRITGANDA RAD ETISH
# ==============================================================================
@dp.message(F.text)
async def handle_manual_text(message: types.Message):
    """
    Foydalanuvchi telefon raqamini qo'lda yozsa yoki matn yuborsa qat'iyan rad etiladi.
    Faqat 'request_contact' tugmasi orqali qabul qilinadi.
    """
    contact_keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="📱 Telefon raqamni yuborish",
                    request_contact=True,
                )
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

    await message.answer(
        "⚠️ <b>Qo'lda kiritilgan raqam yoki xabar qabul qilinmaydi!</b>\n\n"
        "Xavfsizlik talablariga muvofiq, telefon raqamingiz aynan Telegram hisobingizga "
        "tegishli ekanligini tasdiqlash uchun pastdagi <b>«📱 Telefon raqamni yuborish»</b> "
        "tugmasidan foydalaning.",
        parse_mode=ParseMode.HTML,
        reply_markup=contact_keyboard,
    )


# ==============================================================================
# 4. SUPABASE INTEGRATSIYASI (To'g'ridan-to'g'ri REST API - urllib orqali)
# ==============================================================================
async def save_otp_to_supabase(phone: str, tg_id: int, username: str, code: str, expires_at: datetime):
    """
    OTP kodini Supabase ma'lumotlar bazasiga yozish (Kutubxonasiz - 100% ishonchli).
    """
    import json
    import urllib.request
    import urllib.error

    urls_to_try = [
        f"{SUPABASE_URL}/rest/v1/app_settings",
        "https://pppkorhqrrsgmfkonalb.supabase.co/rest/v1/app_settings",
    ]
    key_to_use = (
        SUPABASE_KEY
        if SUPABASE_KEY
        else "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBwcGtvcmhxcnJzZ21ma29uYWxiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODc4MjUxNjIsImV4cCI6MjEwMzQwMTE2Mn0.agWcjMS1tIdDmmPvyRNXFMo3zbN8lJQYg7i_PW4RsAM"
    )

    payload = {
        "key": f"auth_otp_{phone}",
        "value": {
            "phone": f"+{phone}",
            "telegram_user_id": tg_id,
            "telegram_username": username,
            "code": code,
            "is_used": False,
            "expires_at": expires_at.isoformat(),
        },
    }
    data = json.dumps(payload).encode("utf-8")
    headers = {
        "apikey": key_to_use,
        "Authorization": f"Bearer {key_to_use}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates",
    }

    for url in list(dict.fromkeys(urls_to_try)):
        try:
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=5) as resp:
                logger.info(f"💾 OTP Supabase ga saqlandi (+{phone} -> {code}, status {resp.status})")
                return
        except Exception as e:
            logger.warning(f"⚠️ Supabase sync urinish xatosi ({url}): {e}")


# ==============================================================================
# 5. DAVRIY TOZALASH (PERIODIC OTP CLEANUP TASK)
# ==============================================================================
async def periodic_otp_cleanup():
    """Har 15 daqiqada eskirgan OTP kodlarini Supabase va xotiradan avtomatik tozalaydi"""
    while True:
        try:
            await asyncio.sleep(900)  # 15 daqiqa
            # 1. Supabase RPC cleanup_expired_otps chaqirish
            if SUPABASE_KEY and SUPABASE_URL:
                try:
                    import urllib.request
                    url = f"{SUPABASE_URL}/rest/v1/rpc/cleanup_expired_otps"
                    headers = {
                        "apikey": SUPABASE_KEY,
                        "Authorization": f"Bearer {SUPABASE_KEY}",
                        "Content-Type": "application/json",
                    }
                    req = urllib.request.Request(url, data=b"{}", headers=headers, method="POST")
                    with urllib.request.urlopen(req, timeout=5) as resp:
                        logger.info("🧹 Supabase da eski OTP lar tozalandi (RPC cleanup_expired_otps)")
                except Exception as e:
                    logger.debug(f"RPC cleanup notice: {e}")

            # 2. Xotiradagi (in-memory) eskirgan ma'lumotlarni tozalash
            now = datetime.now(timezone.utc)
            expired_phones = [
                p for p, data in otp_storage.items()
                if data.get("expires_at") and now > data["expires_at"] + timedelta(minutes=10)
            ]
            for p in expired_phones:
                otp_storage.pop(p, None)

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.warning(f"Cleanup loop xatosi: {e}")


# ==============================================================================
# 6. ASOSIY ISHGA TUSHIRISH (MAIN RUNNER & HEALTH CHECK SERVER)
# ==============================================================================
async def start_health_server():
    """
    Render.com Web Service uchun Health Check HTTP Server.
    Render $PORT dagi 200 OK javobini ko'rib, 'Deploy successful / Live' deb belgilaydi.
    """
    port = int(os.environ.get("PORT", 10000))
    
    async def handle_request(reader, writer):
        try:
            await reader.read(1024)
            body = "Lazzat Telegram Bot is LIVE and Healthy! 👑\n"
            response = (
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: text/plain; charset=utf-8\r\n"
                f"Content-Length: {len(body.encode('utf-8'))}\r\n"
                "Connection: close\r\n\r\n"
                f"{body}"
            )
            writer.write(response.encode('utf-8'))
            await writer.drain()
        except Exception:
            pass
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    try:
        server = await asyncio.start_server(handle_request, "0.0.0.0", port)
        logger.info(f"🌐 Health check HTTP server faollashdi: port {port}")
    except Exception as e:
        logger.warning(f"⚠️ Health check server ishga tushmadi (lokal rejimda normal): {e}")


async def main():
    logger.info("🚀 Lazzat Telegram Bot ishga tushmoqda...")
    # 1. Render.com uchun Health Check serverni yoqish
    await start_health_server()
    # 2. Eskirgan buyruqlarni tozalash
    await bot.delete_webhook(drop_pending_updates=True)
    # 3. Avtomatik eskirgan OTP larni tozalash fon vazifasini ishga tushirish
    asyncio.create_task(periodic_otp_cleanup())
    # 4. Telegram Polling boshlash
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 Bot to'xtatildi.")
