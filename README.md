# 👑 «LAZZAT» — Rasmiy Telegram Autentifikatsiya Boti

Ushbu bot **«Lazzat» taom yetkazib berish mobil ilovasi** uchun foydalanuvchilarni Telegram orqali xavfsiz ro'yxatdan o'tkazish va tasdiqlash kodlarini (OTP) yetkazib berish xizmatidir.

---

## 🔒 Xavfsizlik Qoidalari & Xususiyatlari:

1. 🇺🇿 **Faqat O'zbekiston Raqamlari**: Faqat `+998...` (12 xonali) raqamlar qabul qilinadi. Boshqa davlat raqamlari rad etiladi.
2. 🚫 **Qo'lda Kiritish Qat'iyan Taqiq**: Foydalanuvchi raqamni klaviaturadan qo'lda yozsa qabul qilinmaydi. Faqat Telegram'ning rasmiy **`«📱 Telefon raqamni yuborish»`** maxsus tugmasi (`request_contact=True`) orqali tasdiqlangan raqam olinadi.
3. 👤 **Kontakt Soxtalashtirishdan Himoya**: Boshqa foydalanuvchining kontaktini forward qilib yuborsa (`contact.user_id != message.from_user.id`) qabul qilinmaydi.
4. ⏳ **2 Daqiqalik Kod Muddati**: Generatsiya qilingan 6 xonali kod faqat **2 daqiqa (120 soniya)** davomida amal qiladi.

---

## 🚀 Ishga Tushirish Qo'llanmasi:

### 1-Qadam: Telegram Bot
* Rasmiy bot manzili: **[@lazzatfod_bot](https://t.me/lazzatfod_bot)**
* BotFather bergan **HTTP API Token**ni nusxalab oling.

### 2-Qadam: Kutubxonalarni O'rnatish
```bash
cd lazzat_telegram_bot
pip install -r requirements.txt
```

### 3-Qadam: `.env` Faylini Sozlash
`.env.example` faylini `.env` deb nusxalang va bot tokeningizni yozing:
```env
BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN_HERE
SUPABASE_URL=https://qfhnzcwkuxdfdsvdpsvx.supabase.co
SUPABASE_KEY=your_supabase_service_role_key
```

### 4-Qadam: Botni Ishga Tushirish
```bash
python bot.py
```

---

## 📊 Supabase Bazasida Jadval Yaratish (SQL):
`create_otp_table.sql` faylidagi buyruqlarni Supabase SQL Editor'ga tashlab ishga tushiring.
