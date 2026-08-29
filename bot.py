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

# Konfiguratsiya
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN_HERE")
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://qfhnzcwkuxdfdsvdpsvx.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

# Logging sozlamalari
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Bot va Dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Xotiradagi OTP saqlash joyi (In-Memory Fallback)
# Format: {phone_number: {"code": "123456", "expires_at": datetime, "user_id": int}}
otp_storage: dict[str, dict] = {}


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

    # Maxsus kontakt so'rash tugmasi (Qo'lda kiritishni oldini olish uchun)
    contact_keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="📱 Telefon raqamni yuborish",
                    request_contact=True,  # Faqat shu tugma orqali haqiqiy raqam olinadi
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
        f"<i>⚠️ Eslatma: Xavfsizlik yuzasidan telefon raqamingiz aynan Telegram "
        f"hisobingizga biriktirilgan bo'lishi shart.</i>"
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

    # Telefon raqamini tozalash
    raw_phone = contact.phone_number.replace("+", "").replace(" ", "").replace("-", "").strip()

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

    # 3-Qadam: 6 xonali xavfsiz OTP kod generatsiya qilish
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

    # Supabase bazasiga saqlash (mavjud bo'lsa)
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
# 4. SUPABASE INTEGRATSIYASI (Yordamchi Funksiya)
# ==============================================================================
async def save_otp_to_supabase(phone: str, tg_id: int, username: str, code: str, expires_at: datetime):
    """
    OTP kodini Supabase ma'lumotlar bazasiga yozish (Flutter ilovasi tekshirishi uchun).
    """
    if not SUPABASE_KEY:
        return

    try:
        from supabase import create_client

        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        supabase.table("telegram_auth_otps").insert({
            "phone_number": f"+{phone}",
            "telegram_user_id": tg_id,
            "telegram_username": username,
            "otp_code": code,
            "is_used": False,
            "expires_at": expires_at.isoformat(),
        }).execute()
        logger.info(f"💾 OTP saved to Supabase for +{phone}")
    except Exception as e:
        logger.warning(f"Supabase sync warning (running in in-memory mode): {e}")


# ==============================================================================
# 5. ASOSIY ISHGA TUSHIRISH (MAIN RUNNER)
# ==============================================================================
async def main():
    logger.info("🚀 Lazzat Telegram Bot ishga tushmoqda...")
    # Eskirgan buyruqlarni tozalash
    await bot.delete_webhook(drop_pending_updates=True)
    # Polling boshlash
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 Bot to'xtatildi.")
