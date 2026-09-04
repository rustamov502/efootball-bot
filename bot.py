import asyncio
import logging
import random
import sqlite3
from aiogram import Bot, Dispatcher, 
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

# --- SOZLAMALAR ---
TOKEN = "8668357270:AAHOLqv3WnGcnjNobLpJG8Ci0YUNi_OZhpQ"
ADMIN_ID = 8451295149
CHANNEL_USERNAME = "@rustamov_tets"  # Majburiy obuna kanali
CHANNEL_LINK = "https://t.me/rustamov_tets"   # Majburiy obuna havolasi
TOURNAMENT_CHANNEL_ID = "@rustamov_tets"  

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
    nickname TEXT,
    full_name TEXT,
    is_active INTEGER DEFAULT 1,
    wins INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS matches (
    match_id TEXT PRIMARY KEY,
    p1_id INTEGER,
    p1_name TEXT,
    p2_id INTEGER,
    p2_name TEXT,
    status TEXT DEFAULT 'pending'
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

reg_data = {}

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
    reg_data.pop(user_id, None)
    
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
        await show_main_menu(call.message)
    else:
        await call.answer("❌ Siz hali kanalga obuna bo'lmadingiz!", show_alert=True)


async def show_main_menu(message: Message):
    buttons = [
        [KeyboardButton(text="🎮 Turnirga ro'yxatdan o'tish"), KeyboardButton(text="📊 Mening holatim")],
        [KeyboardButton(text="📋 Ishtirokchilar ro'yxati"), KeyboardButton(text="ℹ️ Qanday o'ynaladi?")]
    ]
    
    if message.from_user.id == ADMIN_ID:
        buttons.append([KeyboardButton(text="🔒 Ro'yxatdan o'tishni yopish"), KeyboardButton(text="🔓 Ro'yxatdan o'tishni ochish")])
        buttons.append([KeyboardButton(text="🎲 Juftliklarni tuzish"), KeyboardButton(text="⏳ Kutilayotgan natijalar")])
        buttons.append([KeyboardButton(text="📢 Hammga xabar yuborish"), KeyboardButton(text="📊 Turnir statistikasi")])
        buttons.append([KeyboardButton(text="🔄 Turnirni noldan boshlash")])
        
    keyboard = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
    await message.answer("🏆 eFootball Chempionat botiga xush kelibsiz! Kerakli bo'limni tanlang:", reply_markup=keyboard)


@dp.message(F.text == "ℹ️ Qanday o'ynaladi?")
async def how_to_play(message: Message):
    text = (
        "📖 **Turnir qoidalari va ishtirok etish tartibi:**\n\n"
        "1. Ro'yxatdan o'tayotganda o'yin ichidagi **Nickname**ingizni yozasiz.\n"
        "2. Admin juftliklarni tuzgach, sizga lichkangizga raqibingiz va **Match ID** yuboriladi.\n"
        "3. O'yinni o'ynab bo'lgach, g'olib o'yin hisobi tushirilgan **skrinshotni** tashlaydi.\n"
        "4. Rasmning tagiga (caption qismiga) quyidagicha yozasiz:\n"
        "👉 `/result [Match_ID] [Hisob]`\n"
        "*(Misol: `/result m1_1 2:1`)*\n"
        "5. Admin tasdiqlagach, kuchlilar kurashni davom ettiradi!"
    )
    await message.answer(text, parse_mode="Markdown")


@dp.message(F.text == "📋 Ishtirokchilar ro'yxati")
async def show_participants(message: Message):
    cursor.execute("SELECT username, nickname, is_active, wins FROM players")
    all_players = cursor.fetchall()
    
    if not all_players:
        await message.answer("Hozircha turnirga hech kim ro'yxatdan o'tmagan! ❌")
        return
        
    text = f"📋 **Turnir ishtirokchilari (Jami: {len(all_players)} ta):**\n\n"
    for idx, p in enumerate(all_players[:100], 1):
        uname, nick, active, wins = p[0], p[1], p[2], p[3]
        status_icon = "🟢" if active == 1 else "🔴"
        text += f"{idx}. {uname} ({nick}) — {status_icon} (G'alaba: {wins})\n"
        
    if len(all_players) > 100:
        text += f"\n... va yana {len(all_players) - 100} ta o'yinchi bor."
        
    await message.answer(text, parse_mode="Markdown")


@dp.message(F.text == "🎮 Turnirga ro'yxatdan o'tish")
async def register_player_start(message: Message):
    user_id = message.from_user.id

    cursor.execute("SELECT value FROM settings WHERE key = 'reg_status'")
    reg_status = cursor.fetchone()[0]
    
    if reg_status == "closed" and user_id != ADMIN_ID:
        await message.answer("❌ Kechirasiz, hozirda turnir uchun ro'yxatdan o'tish yopilgan!")
        return

    cursor.execute("SELECT * FROM players WHERE user_id = ?", (user_id,))
    if cursor.fetchone():
        await message.answer("Siz allaqachon ro'yxatdan o'tgansiz! ✅")
        return

    username = message.from_user.username
    if not username:
        await message.answer("⚠️ Diqqat! Telegram profilingizda **username (@username)** mavjud emas. Ishtirok etish uchun username ochishingiz shart!", parse_mode="Markdown")
        return

    reg_data[user_id] = "waiting_for_nickname"
    await message.answer("🎮 eFootball o'yinidagi **Nickname**ingizni (ismingizni) kiriting:\n*(Masalan: RUSTAMOV yoki 777_Pro)*")


@dp.message(lambda msg: msg.from_user.id in reg_data and reg_data[msg.from_user.id] == "waiting_for_nickname")
async def process_nickname(message: Message):
    user_id = message.from_user.id
    nickname = message.text.strip()
    username = message.from_user.username
    full_name = message.from_user.full_name
    
    reg_data.pop(user_id, None)

    cursor.execute("INSERT INTO players (user_id, username, nickname, full_name, is_active, wins) VALUES (?, ?, ?, ?, 1, 0)",
                   (user_id, f"@{username}", nickname, full_name))
    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM players")
    count = cursor.fetchone()[0]
    
    await message.answer(
        f"Muvaffaqiyatli ro'yxatdan o'tdingiz! 🎉\n\n"
        f"👤 Telegram: @{username}\n"
        f"🎮 Nickname: {nickname}\n"
        f"📊 Jami ro'yxatdagilar: {count} ta o'yinchi\n\n"
        f"1-tur juftliklari e'lon qilinguncha kuting!"
    )


@dp.message(F.text == "📊 Mening holatim")
async def my_status(message: Message):
    user_id = message.from_user.id
    cursor.execute("SELECT is_active, wins, username, nickname FROM players WHERE user_id = ?", (user_id,))
    player = cursor.fetchone()
    
    if not player:
        await message.answer("Siz hali turnirga ro'yxatdan o'tmagansiz! ❌")
    else:
        status, wins, username, nickname = player
        status_text = "🟢 O'yinda qolyapsiz (Faol)" if status == 1 else "🔴 O'yindan chiqqansiz (Mag'lub)"
        
        text = (
            f"📊 **Sizning turnir ma'lumotlaringiz:**\n\n"
            f"👤 Username: {username}\n"
            f"🎮 Nickname: {nickname}\n"
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


@dp.message(F.text == "🎲 Juftliklarni tuzish")
async def make_pairs(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    cursor.execute("SELECT value FROM settings WHERE key = 'current_round'")
    round_num = int(cursor.fetchone()[0])
    
    cursor.execute("SELECT username, nickname, user_id FROM players WHERE is_active = 1")
    players = list(cursor.fetchall())
    
    if len(players) < 2:
        await message.answer(f"❌ Juftlik tuzish uchun faol o'yinchilar yetarli emas! Faol o'yinchilar soni: {len(players)} ta")
        return
    
    cursor.execute("UPDATE settings SET value = 'closed' WHERE key = 'reg_status'")
    cursor.execute("DELETE FROM matches")
    conn.commit()

    round_title = "🏆 FINAL" if len(players) == 2 else f"🔥 {round_num}-tur"
    random.shuffle(players)
    
    header_text = f"⚔️ **eFootball Chempionat — {round_title}** ⚔️\n👥 Faol o'yinchilar: {len(players)} ta\n"
    await bot.send_message(TOURNAMENT_CHANNEL_ID, header_text, parse_mode="Markdown")
    await message.answer(f"✅ Juftliklar kanalga va o'yinchilarning lichkasiga yuborilmoqda...")
    
    match_counter = 1
    for i in range(0, len(players) - 1, 2):
        p1 = players[i]    
        p2 = players[i+1]  
        
        match_id = f"m{round_num}_{match_counter}"
        match_counter += 1
        
        cursor.execute("INSERT INTO matches (match_id, p1_id, p1_name, p2_id, p2_name, status) VALUES (?, ?, ?, ?, ?, 'pending')",
                       (match_id, p1[2], f"{p1[0]} ({p1[1]})", p2[2], f"{p2[0]} ({p2[1]})"))
        conn.commit()
        
        channel_text = (
            f"🔸 **O'yin juftligi (ID: `{match_id}`):**\n"
            f"1️⃣ {p1[0]} (🎮 {p1[1]})\n"
            f"   ⚔️ VS ⚔️\n"
            f"2️⃣ {p2[0]} (🎮 {p2[1]})\n\n"
            f"📌 *Natija yuborish tartibi:* Skrinshot tashlab, rasm ostiga `/result {match_id} Hisob` deb yozing."
        )
        await bot.send_message(TOURNAMENT_CHANNEL_ID, channel_text, parse_mode="Markdown")
        
        try:
            await bot.send_message(
                p1[2],
                f"🚨 **Sizning navbatdagi o'yiningiz boshlandi!**\n\n"
                f"🆔 Match ID: `{match_id}`\n"
                f"⚔️ Raqibingiz: {p2[0]} (🎮 Nickname: {p2[1]})\n\n"
                f"O'yinni o'ynab bo'lgach, skrinshotni botga tashlang va rasm ostiga quyidagicha yozing:\n"
                f"`/result {match_id} 2:1`",
                parse_mode="Markdown"
            )
        except Exception:
            pass

        try:
            await bot.send_message(
                p2[2],
                f"🚨 **Sizning navbatdagi o'yiningiz boshlandi!**\n\n"
                f"🆔 Match ID: `{match_id}`\n"
                f"⚔️ Raqibingiz: {p1[0]} (🎮 Nickname: {p1[1]})\n\n"
                f"O'yinni o'ynab bo'lgach, skrinshotni botga tashlang va rasm ostiga quyidagicha yozing:\n"
                f"`/result {match_id} 2:1`",
                parse_mode="Markdown"
            )
        except Exception:
            pass
        
    if len(players) % 2 != 0:
        last = players[-1]
        cursor.execute("UPDATE players SET wins = wins + 1 WHERE user_id = ?", (last[2],))
        conn.commit()
        free_text = f"⭐ Bu turda raqibsiz keyingi bosqichga o'tuvchi (Free-win): 📌 {last[0]} (🎮 {last[1]})"
        await bot.send_message(TOURNAMENT_CHANNEL_ID, free_text, parse_mode="Markdown")
        try:
            await bot.send_message(last[2], "⭐ Tabriklaymiz! Bu turda raqibsiz ravishda keyingi bosqichga o'tdingiz!")
        except Exception:
            pass
    
    cursor.execute("UPDATE settings SET value = ? WHERE key = 'current_round'", (str(round_num + 1),))
    conn.commit()
    await message.answer("✅ Barcha juftliklar muvaffaqiyatli tarqatildi!")


@dp.message(F.text == "⏳ Kutilayotgan natijalar")
async def pending_matches_handler(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
        
    cursor.execute("SELECT match_id, p1_name, p2_name FROM matches WHERE status = 'pending'")
    pending = cursor.fetchall()
    
    if not pending:
        await message.answer("✅ Hozirda natijasi kutilayotgan o'yinlar yo'q, hamma o'ynab bo'lgan!")
        return
        
    text = f"⏳ **Hali natija yubormagan juftliklar (Jami: {len(pending)} ta):**\n\n"
    for idx, m in enumerate(pending, 1):
        m_id, p1, p2 = m[0], m[1], m[2]
        text += f"{idx}. [ID: `{m_id}`] — {p1} vs {p2}\n"
        
    await message.answer(text, parse_mode="Markdown")


@dp.message(F.photo)
async def player_send_result_photo(message: Message):
    caption = message.caption
    if not caption or not caption.startswith("/result"):
        return  

    args = caption.split()
    if len(args) < 3:
        await message.answer("❌ Noto'g'ri format! \nRasm ostiga quyidagicha yozing:\n`/result [Match_ID] [Hisob]`\nMasalan: `/result m1_1 2:1`", parse_mode="Markdown")
        return
        
    match_id = args[1]
    score = args[2]
    user_id = message.from_user.id
    
    cursor.execute("SELECT p1_id, p1_name, p2_id, p2_name, status FROM matches WHERE match_id = ?", (match_id,))
    match = cursor.fetchone()
    
    if not match:
        await message.answer("❌ Bunday Match ID topilmadi! Tekshirib qaytadan yozing.")
        return
        
    p1_id, p1_name, p2_id, p2_name, status = match
    
    if user_id != p1_id and user_id != p2_id and user_id != ADMIN_ID:
        await message.answer("❌ Siz bu o'yin ishtirokchisi emassiz!")
        return
        
    if status == 'confirmed':
        await message.answer("⚠️ Bu o'yin natijasi allaqachon tasdiqlangan!")
        return

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=f"✅ {p1_name} yutdi", callback_data=f"appr_{match_id}_{p1_id}_{p2_id}"),
        InlineKeyboardButton(text=f"✅ {p2_name} yutdi", callback_data=f"appr_{match_id}_{p2_id}_{p1_id}")
    )
    
    admin_caption = (
        f"📊 **Yangi o'yin skrinshoti va natijasi!**\n\n"
        f"🆔 Match ID: `{match_id}`\n"
        f"⚔️ O'yin: {p1_name} vs {p2_name}\n"
        f"⚽ Hisob: {score}\n"
        f"👤 Yuborgan o'yinchi: @{message.from_user.username}\n\n"
        f"Pastdagi tugmalar orqali g'olibni tasdiqlang:"
    )
    
    await bot.send_photo(
        chat_id=ADMIN_ID,
        photo=message.photo[-1].file_id,
        caption=admin_caption,
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )
    
    await message.answer("✅ Skrinshot va natija adminga yuborildi! Admin tekshirib tasdiqlagach, xabar olasiz.")


@dp.callback_query(F.data.startswith("appr_"))
async def admin_approve_match(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer("Bu tugma faqat admin uchun! ❌", show_alert=True)
        return
        
    try:
        parts = call.data.split("_")
        match_id = parts[1]
        winner_id = int(parts[2])
        loser_id = int(parts[3])
        
        cursor.execute("UPDATE players SET wins = wins + 1 WHERE user_id = ?", (winner_id,))
        cursor.execute("UPDATE players SET is_active = 0 WHERE user_id = ?", (loser_id,))
        cursor.execute("UPDATE matches SET status = 'confirmed' WHERE match_id = ?", (match_id,))
        conn.commit()
        
        try:
            await bot.send_message(winner_id, "🎉 Tabriklaymiz! Admin skrinshotni tasdiqladi va siz keyingi bosqichga o'tdingiz! 🚀")
        except Exception:
            pass
            
        try:
            await bot.send_message(loser_id, "❌ Afsuski, bu o'yinda mag'lub bo'ldingiz va o'yindan chiqdingiz. Keyingi turnirlarda omad! 🤝")
        except Exception:
            pass
            
        cursor.execute("SELECT COUNT(*) FROM players WHERE is_active = 1")
        active_left = cursor.fetchone()[0]
        if active_left == 1:
            cursor.execute("SELECT username, nickname FROM players WHERE is_active = 1")
            champ = cursor.fetchone()
            champ_text = f"{champ[0]} (🎮 {champ[1]})"
            await bot.send_message(TOURNAMENT_CHANNEL_ID, f"🏆 **TURNIR G'OLIBI (CHEMPION):** {champ_text} 👑\nTabriklaymiz!")
            await bot.send_message(ADMIN_ID, f"🏆 **TURNIR G'OLIBI (CHEMPION):** {champ_text} 👑\nTabriklaymiz!")

        await call.message.edit_caption(caption=f"{call.message.caption}\n\n✅ **Holat:** Admin tomonidan tasdiqlandi va o'yin yopildi!", parse_mode="Markdown")
        await call.answer("Muvaffaqiyatli tasdiqlandi!")
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
    
    cursor.execute("SELECT username, nickname, wins FROM players ORDER BY wins DESC LIMIT 5")
    top_players = cursor.fetchall()
    
    top_text = "\n".join([f"• {p[0]} ({p[1]}) — {p[2]} ta g'alaba" for p in top_players]) if top_players else "Hozircha yo'q"
    
    text = (
        f"📈 **Turnir statistikasi:**\n\n"
        f"🔄 Hozirgi bosqich: {round_num}-tur\n"
        f"👥 Jami ro'yxatdan o'tganlar: {total} ta\n"
        f"🟢 Hozirda o'yinda qolganlar: {active} ta\n\n"
        f"🏆 **Eng kuchli o'yinchilar:**\n{top_text}"
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
    cursor.execute("DELETE FROM matches")
    cursor.execute("UPDATE settings SET value = 'open' WHERE key = 'reg_status'")
    cursor.execute("UPDATE settings SET value = '1' WHERE key = 'current_round'")
    conn.commit()
    await show_main_menu(message)
    await message.answer("Barcha ma'lumotlar tozalandi, turnir noldan boshlashga tayyor! ♻️")


if __name__ == '__main__':
    async def main():
        # Eski aiohttp server olib tashlandi, chunki Render worker sozlamasida 
        # shunchaki long-polling ishlagani qulayroq va xatolik bermaydi.
        await dp.start_polling(bot)

    asyncio.run(main())
