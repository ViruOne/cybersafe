-- ==========================================================
-- 👑 LAZZAT — Telegram Bot OTP Tasdiqlash Jadvali (Supabase)
-- ==========================================================

CREATE TABLE IF NOT EXISTS public.telegram_auth_otps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone_number VARCHAR(20) NOT NULL,
    telegram_user_id BIGINT NOT NULL,
    telegram_username VARCHAR(100),
    otp_code VARCHAR(6) NOT NULL,
    is_used BOOLEAN DEFAULT FALSE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indekslar tezkor qidiruv uchun
CREATE INDEX IF NOT EXISTS idx_telegram_auth_phone ON public.telegram_auth_otps(phone_number);
CREATE INDEX IF NOT EXISTS idx_telegram_auth_otp ON public.telegram_auth_otps(phone_number, otp_code);

-- RLS Xavfsizlik qoidasi
ALTER TABLE public.telegram_auth_otps ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public can verify OTP" ON public.telegram_auth_otps
    FOR SELECT USING (TRUE);

CREATE POLICY "Service role can insert and update OTP" ON public.telegram_auth_otps
    FOR ALL USING (TRUE);
