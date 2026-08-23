from aiohttp import web
import asyncio
import logging
import random
import sqlite3
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
import os

# --- SOZLAMALAR ---
TOKEN = "8668357270:AAEIWlNsYhfIKUsgHs7luacZQf3cg_Yc-HA"
ADMIN_ID = 8451295149
CHANNEL_USERNAME = "@rustamov_tets"  # Kanalingiz username'si
CHANNEL_LINK = "https://t.me/rustamov_tets"   # Kanalingiz havolasi

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- BAZA BILAN ISHLASH ---
conn = sqlite3.connect("tournament_pro.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS players (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    full_name TEXT,
    is_active INTEGER DEFAULT 1,
    wins INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
)
""")
cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('reg_status', 'open')")
cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('current_round', '1')")
conn.commit()


# --- MAJBURIY OBUNANI TEKSHIRISH ---
async def check_subscription(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        if member.status in ["creator", "administrator", "member"]:
            return True
        return False
    except Exception:
        return False


@dp.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    
    # Majburiy obunani tekshirish (Admin uchun majburiy emas)
    is_subbed = await check_subscription(user_id)
    if not is_subbed and user_id != ADMIN_ID:
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="📢 Kanalga obuna bo'lish", url=CHANNEL_LINK))
        builder.row(InlineKeyboardButton(text="✅ Obunani tekshirish", callback_data="check_sub"))
        await message.answer(
            "⚠️ Botdan foydalanish uchun avval quyidagi kanalimizga obuna bo'lishingiz shart!",
            reply_markup=builder.as_markup()
        )
        return

    await show_main_menu(message)


@dp.callback_query(F.data == "check_sub")
async def process_check_sub(call: CallbackQuery):
    user_id = call.from_user.id
    is_subbed = await check_subscription(user_id)
    
    if is_subbed or user_id == ADMIN_ID:
        await call.message.delete()
        await call.message.answer("Rahmat! Obuna tasdiqlandi ✅")
        await show_main_menu_call(call.message)
    else:
        await call.answer("❌ Siz hali kanalga obuna bo'lmadingiz!", show_alert=True)


async def show_main_menu(message: Message):
    buttons = [
        [KeyboardButton(text="🎮 Turnirga ro'yxatdan o'tish"), KeyboardButton(text="📊 Mening holatim")],
        [KeyboardButton(text="📋 Ishtirokchilar ro'yxati")]
    ]
    
    if message.from_user.id == ADMIN_ID:
        buttons.append([KeyboardButton(text="🔒 Ro'yxatdan o'tishni yopish"), KeyboardButton(text="🔓 Ro'yxatdan o'tishni ochish")])
        buttons.append([KeyboardButton(text="🎲 Juftliklarni tuzish"), KeyboardButton(text="📢 Hammga xabar yuborish")])
        buttons.append([KeyboardButton(text="📊 Turnir statistikasi"), KeyboardButton(text="🔄 Turnirni noldan boshlash")])
        
    keyboard = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
    await message.answer("🏆 eFootball Chempionat botiga xush kelibsiz! Kerakli bo'limni tanlang:", reply_markup=keyboard)


async def show_main_menu_call(message: Message):
    buttons = [
        [KeyboardButton(text="🎮 Turnirga ro'yxatdan o'tish"), KeyboardButton(text="📊 Mening holatim")],
        [KeyboardButton(text="📋 Ishtirokchilar ro'yxati")]
    ]
    
    if message.from_user.id == ADMIN_ID:
        buttons.append([KeyboardButton(text="🔒 Ro'yxatdan o'tishni yopish"), KeyboardButton(text="🔓 Ro'yxatdan o'tishni ochish")])
        buttons.append([KeyboardButton(text="🎲 Juftliklarni tuzish"), KeyboardButton(text="📢 Hammga xabar yuborish")])
        buttons.append([KeyboardButton(text="📊 Turnir statistikasi"), KeyboardButton(text="🔄 Turnirni noldan boshlash")])
        
    keyboard = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
    await message.answer("🏆 eFootball Chempionat botiga xush kelibsiz! Kerakli bo'limni tanlang:", reply_markup=keyboard)


# --- ISHTIROKCHILAR RO'YXATI ---
@dp.message(F.text == "📋 Ishtirokchilar ro'yxati")
async def show_participants(message: Message):
    cursor.execute("SELECT username, is_active, wins FROM players")
    all_players = cursor.fetchall()
    
    if not all_players:
        await message.answer("Hozircha turnirga hech kim ro'yxatdan o'tmagan! ❌")
        return
        
    text = "📋 **Turnir ishtirokchilari ro'yxati:**\n\n"
    for idx, p in enumerate(all_players, 1):
        uname, active, wins = p[0], p[1], p[2]
        status_icon = "🟢 O'yinda" if active == 1 else "🔴 O'yindan chiqqan"
        text += f"{idx}. {uname} — {status_icon} (G'alabalar: {wins})\n"
        
    await message.answer(text, parse_mode="Markdown")


@dp.message(F.text == "🎮 Turnirga ro'yxatdan o'tish")
async def register_player(message: Message):
    user_id = message.from_user.id

    cursor.execute("SELECT value FROM settings WHERE key = 'reg_status'")
    reg_status = cursor.fetchone()[0]
    
    if reg_status == "closed" and message.from_user.id != ADMIN_ID:
        await message.answer("❌ Kechirasiz, hozirda turnir uchun ro'yxatdan o'tish yopilgan!")
        return

    cursor.execute("SELECT * FROM players WHERE user_id = ?", (user_id,))
    if cursor.fetchone():
        await message.answer("Siz allaqachon ro'yxatdan o'tgansiz! ✅")
    else:
        username = message.from_user.username
        if not username:
            await message.answer("⚠️ Diqqat! Telegram profilingizda **username (@username)** mavjud emas. Ishtirok etish uchun username ochishingiz shart!", parse_mode="Markdown")
            return
            
        full_name = message.from_user.full_name
        cursor.execute("INSERT INTO players (user_id, username, full_name, is_active, wins) VALUES (?, ?, ?, 1, 0)",
                       (user_id, f"@{username}", full_name))
        conn.commit()
        
        cursor.execute("SELECT COUNT(*) FROM players")
        count = cursor.fetchone()[0]
        await message.answer(f"Muvaffaqiyatli ro'yxatdan o'tdingiz! 🎉\nSizning username: @{username}\nJami ro'yxatdagilar: {count} ta")


@dp.message(F.text == "📊 Mening holatim")
async def my_status(message: Message):
    user_id = message.from_user.id
    cursor.execute("SELECT is_active, wins, username FROM players WHERE user_id = ?", (user_id,))
    player = cursor.fetchone()
    
    if not player:
        await message.answer("Siz hali turnirga ro'yxatdan o'tmagansiz! ❌")
    else:
        status, wins, username = player
        status_text = "🟢 O'yinda qolyapsiz (Faol)" if status == 1 else "🔴 O'yindan chiqqansiz (Mag'lub)"
        
        text = (
            f"📊 **Sizning turnir ma'lumotlaringiz:**\n\n"
            f"👤 Username: {username}\n"
            f"🏆 G'alabalar soni: {wins} ta\n"
            f"📌 Holatingiz: {status_text}"
        )
        await message.answer(text, parse_mode="Markdown")


@dp.message(F.text == "🔒 Ro'yxatdan o'tishni yopish")
async def close_registration(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    cursor.execute("UPDATE settings SET value = 'closed' WHERE key = 'reg_status'")
    conn.commit()
    await message.answer("🔒 Ro'yxatdan o'tish yopildi!")


@dp.message(F.text == "🔓 Ro'yxatdan o'tishni ochish")
async def open_registration(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    cursor.execute("UPDATE settings SET value = 'open' WHERE key = 'reg_status'")
    conn.commit()
    await message.answer("🔓 Ro'yxatdan o'tish ochildi!")


# --- JUFTLIKLARNI TUZISH (Barcha turlarda userlar chiqishi ta'minlandi) ---
@dp.message(F.text == "🎲 Juftliklarni tuzish")
async def make_pairs(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    cursor.execute("SELECT value FROM settings WHERE key = 'current_round'")
    round_num = int(cursor.fetchone()[0])
    
    cursor.execute("SELECT username, user_id FROM players WHERE is_active = 1")
    players = list(cursor.fetchall())
    
    if len(players) < 2:
        await message.answer(f"❌ Juftlik tuzish uchun faol o'yinchilar yetarli emas! Faol o'yinchilar soni: {len(players)} ta")
        return
    
    cursor.execute("UPDATE settings SET value = 'closed' WHERE key = 'reg_status'")
    conn.commit()

    round_title = "🏆 FINAL" if len(players) == 2 else f"🔥 {round_num}-tur"
    random.shuffle(players)
    
    await message.answer(f"⚔️ **{round_title} (Faol o'yinchilar: {len(players)} ta)** ⚔️", parse_mode="Markdown")
    
    for i in range(0, len(players) - 1, 2):
        p1 = players[i]    # p1[0] -> username, p1[1] -> user_id
        p2 = players[i+1]  # p2[0] -> username, p2[1] -> user_id
        
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text=f"🏆 G'olib: {p1[0]}", callback_data=f"win_{p1[1]}_lose_{p2[1]}"),
            InlineKeyboardButton(text=f"🏆 G'olib: {p2[0]}", callback_data=f"win_{p2[1]}_lose_{p1[1]}")
        )
        
        text = f"🔸 **O'yin juftligi:**\n1️⃣ {p1[0]}\n   ⚔️ VS ⚔️\n2️⃣ {p2[0]}"
        await message.answer(text, reply_markup=builder.as_markup(), parse_mode="Markdown")
        
    if len(players) % 2 != 0:
        last = players[-1]
        await message.answer(f"⭐ Bu turda raqibsiz keyingi bosqichga o'tuvchi (Free-win):\n📌 {last[0]}", parse_mode="Markdown")
    
    cursor.execute("UPDATE settings SET value = ? WHERE key = 'current_round'", (str(round_num + 1),))
    conn.commit()


@dp.callback_query(F.data.startswith("win_"))
async def process_match_result(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer("Bu tugma faqat admin uchun! ❌", show_alert=True)
        return
    
    try:
        data_parts = call.data.split("_")
        winner_id = int(data_parts[1])
        loser_id = int(data_parts[3])
        
        cursor.execute("UPDATE players SET wins = wins + 1 WHERE user_id = ?", (winner_id,))
        cursor.execute("UPDATE players SET is_active = 0 WHERE user_id = ?", (loser_id,))
        conn.commit()
        
        try:
            await bot.send_message(winner_id, "🎉 Tabriklaymiz! Siz o'yinda g'alaba qozonib, keyingi bosqichga chiqdingiz! 🚀")
        except Exception:
            pass
            
        try:
            await bot.send_message(loser_id, "❌ Afsuski, bu o'yinda mag'lub bo'ldingiz va o'yindan chiqdingiz. Keyingi chempionatlarda ko'rishguncha! 🤝")
        except Exception:
            pass
            
        cursor.execute("SELECT COUNT(*) FROM players WHERE is_active = 1")
        active_left = cursor.fetchone()[0]
        if active_left == 1:
            cursor.execute("SELECT username FROM players WHERE is_active = 1")
            champ = cursor.fetchone()[0]
            await bot.send_message(ADMIN_ID, f"🏆 **TURNIR G'OLIBI (CHEMPION):** {champ} 👑\nTabriklaymiz!")

        await call.message.edit_text(f"{call.message.text}\n\n✅ **Natija saqlandi:** G'olib keyingi bosqichga o'tkazildi!", parse_mode="Markdown")
        await call.answer("Natija saqlandi!")
    except Exception as e:
        await call.answer(f"Xatolik: {e}", show_alert=True)


@dp.message(F.text == "📊 Turnir statistikasi")
async def admin_stats(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
        
    cursor.execute("SELECT value FROM settings WHERE key = 'current_round'")
    r_val = cursor.fetchone()
    round_num = int(r_val[0]) - 1 if r_val else 1
    
    cursor.execute("SELECT COUNT(*) FROM players WHERE is_active = 1")
    active = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM players")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT username, wins FROM players ORDER BY wins DESC LIMIT 5")
    top_players = cursor.fetchall()
    
    top_text = "\n".join([f"• {p[0]} — {p[1]} ta g'alaba" for p in top_players]) if top_players else "Hozircha yo'q"
    
    text = (
        f"📈 **Turnir statistikasi:**\n\n"
        f"🔄 Hozirgi bosqich: {round_num}-tur\n"
        f"👥 Jami ro'yxatdan o'tganlar: {total} ta\n"
        f"🟢 Hozirda o'yinda qolganlar: {active} ta\n\n"
        f"🏆 **Eng faol o'yinchilar:**\n{top_text}"
    )
    await message.answer(text, parse_mode="Markdown")


@dp.message(F.text == "📢 Hammga xabar yuborish")
async def ask_broadcast(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("Barcha ishtirokchilarga yubormoqchi bo'lgan xabaringizni yuboring (boshiga `/bc ` qo'shib yozing):\n\nMasalan: `/bc E'lon: O'yinlar boshlandi!`")


@dp.message(Command("bc"))
async def broadcast_message(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    text = message.text.replace("/bc", "").strip()
    cursor.execute("SELECT user_id FROM players")
    users = cursor.fetchall()
    
    success = 0
    for u in users:
        try:
            await bot.send_message(u[0], f"📢 **Turnir e'loni:**\n\n{text}", parse_mode="Markdown")
            success += 1
        except Exception:
            pass
            
    await message.answer(f"Xabar {success} ta ishtirokchiga muvaffaqiyatli yuborildi! 🚀")


@dp.message(F.text == "🔄 Turnirni noldan boshlash")
async def reset_all(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    cursor.execute("DELETE FROM players")
    cursor.execute("UPDATE settings SET value = 'open' WHERE key = 'reg_status'")
    cursor.execute("UPDATE settings SET value = '1' WHERE key = 'current_round'")
    conn.commit()
    await show_main_menu(message)
    await message.answer("Barcha ma'lumotlar tozalandi, turnir noldan boshlashga tayyor! ♻️")


# --- RENDER UCHUN MINI VEB-SERVER QISMI ---
routes = web.RouteTableDef()

@routes.get("/")
async def handle_ping(request):
    return web.Response(text="Bot is running!")

async def web_server():
    app = web.Application()
    app.add_routes(routes)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()


if __name__ == '__main__':
    async def main():
        await web_server()
        await dp.start_polling(bot)

    asyncio.run(main())
