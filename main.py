import asyncio
import io
import os
import re
import time
import requests
import urllib3
from Crypto.Cipher import AES
from aiohttp import web
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)
from telegram.constants import ParseMode

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==========================================
# التوكن — يقرأ من متغير البيئة (Render)
# ==========================================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
PORT = int(os.environ.get("PORT", "8080"))


# ==========================================
# BIO SETTER — UNTOUCHED
# ==========================================
K = b'Yg&tc%DEuh6%Zc^8'
V = b'6oyZDr22E3ychjM%'

def vr(n):
    d = []
    while True:
        b = n & 0x7F
        n >>= 7
        if n: b |= 0x80
        d.append(b)
        if not n: break
    return bytes(d)

def pb(F):
    p = bytearray()
    for f, v in F.items():
        if isinstance(v, bool):
            p.extend(vr((f << 3) | 0)); p.extend(vr(1 if v else 0))
        elif isinstance(v, int):
            p.extend(vr((f << 3) | 0)); p.extend(vr(v))
        elif isinstance(v, str):
            d = v.encode(); p.extend(vr((f << 3) | 2)); p.extend(vr(len(d))); p.extend(d)
        elif isinstance(v, (bytes, bytearray)):
            d = bytes(v); p.extend(vr((f << 3) | 2)); p.extend(vr(len(d))); p.extend(d)
    return bytes(p)

def enc(p):
    pl = 16 - (len(p) % 16)
    return AES.new(K, AES.MODE_CBC, V).encrypt(p + bytes([pl]*pl))

def encrypt_bio(bio):
    f = {2: 17, 8: bio, 9: 1}
    raw = pb(f)
    return " ".join(f"{b:02X}" for b in enc(raw))

def send_api(hex_data, token):
    H = {"User-Agent": "UnityPlayer/2018.4.12f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)", "Accept": "*/*", "Accept-Encoding": "deflate, gzip", "X-GA-SV": str(int(time.time())), "Authorization": f"Bearer {token}", "X-GA": "v1 1", "ReleaseVersion": "OB55", "Content-Type": "application/x-www-form-urlencoded", "X-Unity-Version": "2018.4.12f1"}
    try:
        r = requests.post("https://clientbp.ppmainecoonghj.com/UpdateSocialBasicInfo",
                          headers=H,
                          data=bytes.fromhex(hex_data.replace(" ", "")),
                          timeout=15, verify=False)
        return r.status_code, r.text
    except Exception as e:
        return 500, str(e)


# ==========================================
# LOGIN: uid:pw → JWT
# ==========================================
def oauth_login(uid, pwd):
    H = {"User-Agent": "GarenaMSDK/4.0.19P4(G011A ;Android 9;en;US;)",
         "Content-Type": "application/x-www-form-urlencoded"}
    try:
        r = requests.post(
            "https://100067.connect.garena.com/oauth/guest/token/grant",
            headers=H,
            data={"uid": uid, "password": pwd, "response_type": "token",
                  "client_type": "2", "client_id": "100067"},
            verify=False, timeout=15
        )
    except Exception:
        return None
    if r.status_code != 200:
        return None
    try:
        j = r.json()
    except Exception:
        return None
    if "error" in j:
        return None
    if "access_token" not in j or "open_id" not in j:
        return None
    return j["access_token"], j["open_id"]

def _vr_parse(data, pos):
    r = 0; s = 0
    while pos < len(data):
        b = data[pos]; pos += 1
        r |= (b & 0x7F) << s
        if not (b & 0x80):
            break
        s += 7
    return r, pos

def _parse_proto(data):
    f = {}; pos = 0; n = len(data)
    while pos < n:
        try:
            k, pos = _vr_parse(data, pos)
        except Exception:
            break
        fn = k >> 3; wt = k & 7
        try:
            if wt == 0:
                v, pos = _vr_parse(data, pos)
            elif wt == 2:
                ln, pos = _vr_parse(data, pos); v = data[pos:pos+ln]; pos += ln
            else:
                break
        except Exception:
            break
        f.setdefault(fn, []).append(v)
    return f

def major_login(at, oi):
    P = {}
    P[3] = time.strftime("%Y-%m-%d %H:%M:%S")
    P[4] = "free fire"; P[5] = 1; P[7] = "1.132.9"
    P[8] = "Android OS 14 / API-34 (UP1A.231005.007/V816.0.15.0.UNQMIXM)"
    P[9] = "Handheld"; P[10] = "Grameenphone"; P[11] = "CarrierDataNetwork"
    P[12] = 1666; P[13] = 750; P[14] = "352"; P[15] = "ARM64 FP ASIMD AES | 2400 | 8"
    P[16] = 5563; P[17] = "Mali-G57 MC2"
    P[18] = "OpenGL ES 3.2 v1.r32p1-01eac0.0a0b917d9265b4c01be9925306306139"
    P[19] = "Google|9cc73f7a-91f6-40f6-87ec-5b67e597eb8c"; P[20] = "59.152.5.188"
    P[21] = "en"; P[22] = oi; P[23] = "8"; P[24] = "Handheld"
    P[25] = "Xiaomi 2312DRAABI"; P[26] = "BD"; P[29] = at; P[30] = 1
    P[41] = "Grameenphone"; P[42] = "Cellular"
    P[57] = "7428b253defc164018c604a1ebbfebdf"
    P[60] = 109685; P[61] = 58294; P[62] = 797; P[63] = 18000; P[64] = 58818; P[65] = 109685
    P[66] = 58818; P[67] = 109685; P[73] = 2
    P[74] = "/data/app/~~cqQgpdMykLQEM3odipXatw==/com.dts.freefireth-G6e5yOt1dtuXG5Ambhj18g==/lib/arm64"
    P[76] = 1
    P[77] = "b8e0cd5e295eee42f5860d3c86e483dd|/data/app/~~cqQgpdMykLQEM3odipXatw==/com.dts.freefireth-G6e5yOt1dtuXG5Ambhj18g==/base.apk"
    P[78] = 3; P[79] = 2; P[81] = "64"; P[83] = "2019121229"; P[85] = 3; P[86] = "OpenGLES2"
    P[87] = 4095; P[88] = 8
    P[89] = b"FwQVTgUPX1UaUllDDwcWCRBpWAUOUgsvA1snWlBaO1kFYg=="
    P[90] = "Dhaka"; P[91] = "C"; P[92] = 8043; P[93] = "android"
    P[94] = "KqsHT4XbSZhqerDNUhjbS3DxG/4+I62zQU2tZFJN91kBUICAlZ5yujshLKvjlk/KiShfKfis8EeB1PMhFHIodWPncZC4fCHYF3TcTwNj95aWY/S3"
    P[95] = 111207; P[96] = '{"cur_rate":[60,90,120],"support_etc2":false}'
    P[97] = 1; P[98] = 1; P[99] = "4"; P[100] = "4"; P[102] = "GQ]        e"; P[103] = 1
    P[104] = 45174; P[105] = 1
    P[106] = "https://dl-bs.ggpolarbear.com/live/ABHotUpdates/|https://core-bs.ggpolarbear.com/live/ABHotUpdates/|a4332cb1c1a84e51dd77441e4856ed5a"
    P[107] = "1.9393e7b8e53e8aeb"

    H = {"User-Agent": "UnityPlayer/2018.4.12f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)",
         "Accept": "*/*", "Accept-Encoding": "deflate, gzip",
         "X-GA-SV": str(int(time.time())), "Authorization": "Bearer ",
         "X-GA": "v1 1", "ReleaseVersion": "OB55",
         "Content-Type": "application/x-www-form-urlencoded",
         "X-Unity-Version": "2018.4.12f1"}
    raw = pb(P)
    payload = enc(raw)
    try:
        r = requests.post("https://loginbp.ppmainecoonghj.com/MajorLogin",
                          headers=H, data=payload, verify=False, timeout=20)
    except Exception:
        return None
    if r.status_code not in (200, 201) or not r.content:
        return None
    f = _parse_proto(r.content)
    jwt_raw = f.get(8, [None])[0]
    if not jwt_raw and len(r.content) > 64:
        f = _parse_proto(r.content[64:])
        jwt_raw = f.get(8, [None])[0]
    if isinstance(jwt_raw, bytes):
        try:
            return jwt_raw.decode()
        except Exception:
            return None
    return jwt_raw

def get_jwt(uid, pwd):
    oauth = oauth_login(uid, pwd)
    if not oauth:
        return None, "OAuth failed (wrong credentials or banned)"
    at, oi = oauth
    jwt = major_login(at, oi)
    if not jwt:
        return None, "MajorLogin failed"
    return jwt, None


# ==========================================
# ACCOUNT PARSER
# ==========================================
def parse_accounts(text):
    accounts = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = re.split(r'[:|,\s]+', line)
        parts = [p.strip() for p in parts if p.strip()]
        if len(parts) < 2:
            continue
        a, b = parts[0], parts[1]
        if a.isdigit() and 7 <= len(a) <= 12:
            uid, pwd = a, b
        elif b.isdigit() and 7 <= len(b) <= 12:
            uid, pwd = b, a
        else:
            continue
        accounts.append((uid, pwd))
    return accounts


# ==========================================
# PROCESS ONE
# ==========================================
def process_one(uid, pwd, encrypted_bio):
    jwt, err = get_jwt(uid, pwd)
    if not jwt:
        return False, err
    status, _ = send_api(encrypted_bio, jwt)
    if status == 200:
        return True, "OK"
    return False, f"HTTP {status}"


# ==========================================
# TELEGRAM HANDLERS
# ==========================================
WAITING_ACCOUNTS, WAITING_BIO = range(2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['accounts'] = []
    text = (
        "🔹 <b>Bio Setter Bot</b>\n\n"
        "Send accounts in any of these formats (one per line):\n\n"
        "• <code>uid:password</code>\n"
        "• <code>password:uid</code>\n"
        "• <code>uid,password</code>\n"
        "• <code>uid password</code>\n\n"
        "Or upload a <b>.txt</b> file 📄\n\n"
        "Send /done when finished, or /cancel to reset."
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)
    return WAITING_ACCOUNTS

async def handle_accounts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = None
    if update.message.document:
        try:
            file = await update.message.document.get_file()
            buf = io.BytesIO()
            await file.download_to_memory(buf)
            text = buf.getvalue().decode("utf-8", errors="ignore")
        except Exception as e:
            await update.message.reply_text(f"❌ File read error: {e}")
            return WAITING_ACCOUNTS
    elif update.message.text:
        text = update.message.text
    else:
        return WAITING_ACCOUNTS

    parsed = parse_accounts(text)
    if not parsed:
        await update.message.reply_text("❌ No valid accounts found. Try again or /cancel.")
        return WAITING_ACCOUNTS

    existing = context.user_data.get('accounts', [])
    existing.extend(parsed)
    context.user_data['accounts'] = existing

    await update.message.reply_text(
        f"✅ Added <b>{len(parsed)}</b> accounts.\n"
        f"📊 Total: <b>{len(existing)}</b>\n\n"
        f"Send more, or /done to continue.",
        parse_mode=ParseMode.HTML
    )
    return WAITING_ACCOUNTS

async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    accounts = context.user_data.get('accounts', [])
    if not accounts:
        await update.message.reply_text("❌ No accounts. Use /start to begin.")
        return ConversationHandler.END

    await update.message.reply_text(
        f"✅ <b>{len(accounts)}</b> accounts saved.\n\n"
        f"📝 Send the <b>bio</b> you want to set (max <b>160</b> chars):",
        parse_mode=ParseMode.HTML
    )
    return WAITING_BIO

async def handle_bio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bio = update.message.text.strip()
    if not bio:
        await update.message.reply_text("❌ Empty. Try again.")
        return WAITING_BIO
    if len(bio) > 160:
        await update.message.reply_text(f"❌ Too long ({len(bio)}/160). Try again.")
        return WAITING_BIO

    accounts = context.user_data.get('accounts', [])
    encrypted = encrypt_bio(bio)

    status_msg = await update.message.reply_text(
        f"⏳ Processing {len(accounts)} accounts...\n"
        f"📝 Bio: <code>{bio}</code>",
        parse_mode=ParseMode.HTML
    )

    asyncio.create_task(_process_all(context, accounts, encrypted, bio, status_msg))
    return ConversationHandler.END

async def _process_all(context, accounts, encrypted_bio, bio, status_msg):
    success = 0
    failed = 0
    results = []

    for i, (uid, pwd) in enumerate(accounts, 1):
        try:
            ok, msg = await asyncio.to_thread(process_one, uid, pwd, encrypted_bio)
        except Exception as e:
            ok, msg = False, str(e)[:60]

        if ok:
            success += 1
            results.append(f"✅ <code>{uid}</code>: {msg}")
        else:
            failed += 1
            results.append(f"❌ <code>{uid}</code>: {msg}")

        if i % 5 == 0 or i == len(accounts):
            try:
                await status_msg.edit_text(
                    f"⏳ Progress: {i}/{len(accounts)}\n"
                    f"✅ {success}  ❌ {failed}",
                    parse_mode=ParseMode.HTML
                )
            except Exception:
                pass

        await asyncio.sleep(0.4)

    summary = (
        f"🎯 <b>Finished!</b>\n\n"
        f"✅ Success: <b>{success}</b>\n"
        f"❌ Failed: <b>{failed}</b>\n"
        f"📝 Bio: <code>{bio}</code>"
    )

    if results:
        detail = "\n".join(results[:25])
        if len(results) > 25:
            detail += f"\n… +{len(results) - 25} more"
        summary += f"\n\n<b>Details:</b>\n{detail}"

    try:
        await status_msg.edit_text(summary, parse_mode=ParseMode.HTML)
    except Exception:
        await context.bot.send_message(
            status_msg.chat_id, summary, parse_mode=ParseMode.HTML
        )

    context.user_data['accounts'] = []

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['accounts'] = []
    await update.message.reply_text("❌ Cancelled. Use /start to begin again.")
    return ConversationHandler.END


# ==========================================
# WEB SERVER (للـ health check في Render)
# ==========================================
async def _health(request):
    return web.Response(text="OK", status=200)

async def _root(request):
    return web.Response(text="XORE Bio Bot Running ✅", status=200)

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", _root)
    app.router.add_get("/health", _health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"🌐 Web server listening on port {PORT}")


# ==========================================
# MAIN — Bot + Web server في نفس الوقت
# ==========================================
async def main():
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN env var not set!")
        return

    # 1. شغل سيرفر الويب (Render health check)
    await start_web_server()

    # 2. جهز بوت التليجرام
    application = Application.builder().token(BOT_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            WAITING_ACCOUNTS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_accounts),
                MessageHandler(filters.Document.ALL, handle_accounts),
                CommandHandler("done", done),
            ],
            WAITING_BIO: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_bio),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(conv)

    # 3. ابدأ البوت يدوياً (بدون run_polling اللي يحجب async)
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    print("🤖 Telegram bot polling started")

    # 4. ابقَ شغالاً للأبد
    try:
        await asyncio.Event().wait()
    finally:
        print("🛑 Shutting down...")
        await application.updater.stop()
        await application.stop()
        await application.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
