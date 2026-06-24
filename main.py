import telebot
from telebot import types
import random
from flask import Flask
from threading import Thread
import os
import time

TOKEN = '8777992778:AAE-yWMJpVvqaIPT-qh4lGGUNqtIcDAlIxI'
bot = telebot.TeleBot(TOKEN)

# --- БАЗЫ ДАННЫХ В ПАМЯТИ ---
user_characters = {}  
user_balances = {}    
user_inventory = {}   
last_spin = {}        
active_duels = {}     

ROULETTE_COOLDOWN = 7200 
TURN_TIMEOUT = 60
TIMEOUT_PENALTY = 500

# --- БАЗА ФОТО ПЕРСОНАЖЕЙ ---
CHARACTER_PHOTOS = {
    "Усопп": "https://static.wikia.nocookie.net/onepiece/images/f/f6/Usopp_Anime_Post_Timeskip_Infobox.png",
    "Зоро": "https://static.wikia.nocookie.net/onepiece/images/4/4e/Roronoa_Zoro_Anime_Post_Timeskip_Infobox.png"
}

# --- МИНИ ВЕБ-СЕРВЕР ДЛЯ RENDER ---
app = Flask('')
@app.route('/')
def home(): return "Бот Bounty Hunt онлайн и готов к бою!"
def run_flask(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
Thread(target=run_flask).start()


# --- КЛАВИАТУРЫ ---
def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🎯 Персонажи / Магазин", "🎰 Рулетка")
    markup.add("📊 Мой профиль")
    return markup

def get_battle_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("⚔️ Атака", "🛡️ Защита")
    return markup


# --- ПРОВЕРКА ТАЙМАУТА ---
def check_duel_timeout(chat_id):
    if chat_id not in active_duels:
        return False
        
    duel = active_duels[chat_id]
    current_time = time.time()
    
    if current_time - duel['last_action_time'] > TURN_TIMEOUT:
        loser_id = duel['turn']
        if loser_id == duel['p1']:
            loser_name = duel['p1_name']
            winner_name = duel['p2_name']
        else:
            loser_name = duel['p2_name']
            winner_name = duel['p1_name']
            
        user_balances[loser_id] = max(0, user_balances.get(loser_id, 0) - TIMEOUT_PENALTY)
        
        try:
            bot.edit_message_text(
                chat_id=chat_id, message_id=duel['msg_id'],
                text=f"⏱ **Бой завершен по таймауту!**\n{loser_name} слишком долго думал."
            )
        except: pass
        
        bot.send_message(chat_id, 
                         f"⏱ **ВРЕМЯ ИСТЕКЛО!**\n\n"
                         f"💀 Игрок **{loser_name}** исключен из боя за бездействие!\n"
                         f"🏆 Победитель: **{winner_name}**\n"
                         f"💸 С баланса {loser_name} списано **{TIMEOUT_PENALTY} Белли** штрафа.")
                         
        del active_duels[chat_id]
        return True
    return False


# --- СТАРТ ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    uid = message.from_user.id
    if uid not in user_inventory: user_inventory[uid] = ["Усопп"]
    if uid not in user_characters: user_characters[uid] = "Усопп"
        
    bot.reply_to(message, 
                 "🏴‍☠️ Добро пожаловать в мир One Piece Bounty Hunt!", 
                 reply_markup=get_main_keyboard())


# --- РУЛЕТКА ---
@bot.message_handler(func=lambda m: m.text == "🎰 Рулетка")
def daily_roulette(message):
    uid = message.from_user.id
    current_time = time.time()
    
    if uid in last_spin:
        time_passed = current_time - last_spin[uid]
        if time_passed < ROULETTE_COOLDOWN:
            time_left = int(ROULETTE_COOLDOWN - time_passed)
            hours = time_left // 3600
            minutes = (time_left % 3600) // 60
            bot.reply_to(message, f"⏳ Колесо перезаряжается! Приходи через **{hours} ч. {minutes} мин.**")
            return

    roll = random.random() * 100
    if roll < 40: prize = 100
    elif roll < 70: prize = 300
    elif roll < 90: prize = 500
    elif roll < 97.5: prize = 700
    else: prize = 1000

    user_balances[uid] = user_balances.get(uid, 0) + prize
    last_spin[uid] = current_time
    
    bot.reply_to(message, 
                 f"🎰 **Рулетка One Piece**\n"
                 f"━︎━︎━︎━︎━︎━︎━︎━︎━︎━︎\n"
                 f"🔹 100 Белли — 40%\n"
                 f"🔹 300 Белли — 30%\n"
                 f"🔹 500 Белли — 20%\n"
                 f"🔹 700 Белли — 7.5%\n"
                 f"🔹 1000 Белли — 2.5%\n"
                 f"━︎━︎━︎━︎━︎━︎━︎━︎━︎━_\n"
                 f"🎉 Тебе выпало: **{prize} Белли!**\n"
                 f"💰 Твой баланс: **{user_balances[uid]} Белли**.", 
                 parse_mode="Markdown")


# --- МАГАЗИН ПЕРСОНАЖЕЙ ---
@bot.message_handler(func=lambda m: m.text == "🎯 Персонажи / Магазин")
def show_shop(message):
    uid = message.from_user.id
    if uid not in user_inventory: user_inventory[uid] = ["Усопп"]
        
    bal = user_balances.get(uid, 0)
    current_char = user_characters.get(uid, "Не выбран")
    
    shop_photo = "https://w7.pngwing.com/pngs/307/707/png-transparent-one-piece-pirate-warriors-3-one-piece-bounty-rush-anime-treasure-chest-one-piece-miscellaneous-text-logo.png"
    
    text = (f"🛒 **МАГАЗИН ПИРАТОВ**\n\n"
            f"👤 Твой боец: **{current_char}**\n"
            f"💰 Баланс: **{bal} Белли**\n\n"
            f"📜 Доступный ростер:\n"
            f"1. **Усопп** — Бесплатно (Стартовый)\n"
            f"2. **Зоро** — 300 Белли\n\n"
            f"Управляй командой кнопками ниже:")
            
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("🎯 Выбрать Усоппа", callback_data="set_Усопп"))
    
    if "Зоро" in user_inventory[uid]:
        markup.add(types.InlineKeyboardButton("⚔️ Выбрать Зоро", callback_data="set_Зоро"))
    else:
        markup.add(types.InlineKeyboardButton("🟢 Купить Зоро (300 Белли)", callback_data="buy_Зоро"))
        
    bot.send_photo(message.chat.id, shop_photo, caption=text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: True)
def handle_shop_buttons(call):
    uid = call.from_user.id
    action = call.data
    if uid not in user_inventory: user_inventory[uid] = ["Усопп"]

    if action.startswith("set_"):
        char_name = action.split("_")[1]
        user_characters[uid] = char_name
        bot.edit_message_caption(
            chat_id=call.message.chat.id, message_id=call.message.message_id, 
            caption=f"✅ Успешно выбран персонаж: **{char_name}**!", parse_mode="Markdown"
        )
    elif action == "buy_Зоро":
        bal = user_balances.get(uid, 0)
        if bal >= 300:
            user_balances[uid] = bal - 300
            user_inventory[uid].append("Зоро")
            user_characters[uid] = "Зоро"
            bot.edit_message_caption(
                chat_id=call.message.chat.id, message_id=call.message.message_id, 
                caption="⚔️ Ты успешно приобрёл и экипировал **Зоро**!", parse_mode="Markdown"
            )
        else:
            bot.answer_callback_query(call.id, "❌ Недостаточно Белли!", show_alert=True)


# --- ПРОФИЛЬ ---
@bot.message_handler(func=lambda m: m.text == "📊 Мой профиль")
def show_profile(message):
    uid = message.from_user.id
    char = user_characters.get(uid, "Усопп")
    bal = user_balances.get(uid, 0)
    inv = ", ".join(user_inventory.get(uid, ["Усопп"]))
    bot.reply_to(message, f"📋 **ПРОФИЛЬ ПИРАТА:**\n\n👤 Боец: *{char}*\n💰 Баланс: *{bal} Белли*\n🎒 Команда: *{inv}*", parse_mode="Markdown")


# --- ЛОГИКА БОЯ (ИСПРАВЛЕН БАГ ЗАВИСАНИЯ + КОМАНДА "ХАНТ") ---
@bot.message_handler(func=lambda m: m.text and m.text.lower() == "хант")
def start_bounty_hunt(message):
    if message.chat.type == 'private':
        bot.reply_to(message, "Эту команду нужно писать в чате в ответ на сообщение соперника!")
        return
    if not message.reply_to_message:
        bot.reply_to(message, "Напиши 'хант' в ответ на сообщение соперника!")
        return

    p1_id, p2_id = message.from_user.id, message.reply_to_message.from_user.id
    p1_name, p2_name = message.from_user.first_name, message.reply_to_message.from_user.first_name

    if p1_id == p2_id:
        bot.reply_to(message, "Нельзя нападать на самого себя!")
        return

    chat_id = message.chat.id
    
    if chat_id in active_duels:
        if not check_duel_timeout(chat_id):
            bot.reply_to(message, "В этом чате уже идет битва! Подождите ее окончания.")
            return

    p1_char = user_characters.get(p1_id, "Усопп")
    p2_char = user_characters.get(p2_id, "Усопп")

    fighters = [p1_id, p2_id]
    first_turn = random.choice(fighters)
    first_name = p1_name if first_turn == p1_id else p2_name

    # ИСПРАВЛЕНИЕ: Сразу формируем и отправляем готовый стартовый текст без промежуточных "инициализаций"
    start_text = (f"🏴‍☠️ **БАУНТИ ХАНТ НАЧАТ!** 🏴‍☠️\n\n"
                  f"👤 {p1_name} ({p1_char}) 🆚 👤 {p2_name} ({p2_char})\n\n"
                  f"❤️ {p1_name}: 100 HP\n"
                  f"❤️ {p2_name}: 100 HP\n\n"
                  f"👉 Первым ходит: **{first_name}**!")

    msg = bot.send_message(chat_id, start_text, reply_markup=get_battle_keyboard())

    active_duels[chat_id] = {
        'p1': p1_id, 'p1_name': p1_name, 'p1_char': p1_char, 'p1_hp': 100, 'p1_status': 'normal',
        'p2': p2_id, 'p2_name': p2_name, 'p2_char': p2_char, 'p2_hp': 100, 'p2_status': 'normal',
        'turn': first_turn,
        'msg_id': msg.message_id,
        'last_action_time': time.time()
    }

    try: bot.delete_message(chat_id, message.message_id)
    except: pass


@bot.message_handler(func=lambda m: m.text in ["⚔️ Атака", "🛡️ Защита"])
def handle_battle_turn(message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    try: bot.delete_message(chat_id, message.message_id)
    except: pass

    if chat_id not in active_duels: return
    if check_duel_timeout(chat_id): return

    duel = active_duels[chat_id]

    if user_id != duel['turn']: return

    if user_id == duel['p1']: curr, opp = 'p1', 'p2'
    else: curr, opp = 'p2', 'p1'

    action = message.text
    log_msg = ""

    if action == "🛡️ Защита":
        duel[curr + '_status'] = 'defending'
        log_msg = f"🛡️ **{duel[curr+'_name']}** встал в блок."
    elif action == "⚔️ Атака":
        min_dmg, max_dmg = (18, 28) if duel[curr+'_char'] == "Зоро" else (15, 25)
        damage = random.randint(min_dmg, max_dmg)
        
        if duel[opp + '_status'] == 'defending':
            damage = int(damage * 0.3)
            duel[opp + '_status'] = 'normal'
            log_msg = f"⚔️ **{duel[curr+'_name']}** атакует в блок! Нанесено {damage} урона."
        else:
            log_msg = f"⚔️ **{duel[curr+'_name']}** наносит удар! Нанесено {damage} урона."
        
        duel[opp + '_hp'] = max(0, duel[opp + '_hp'] - damage)

    # ПРОВЕРКА НА ПОБЕДУ
    if duel[opp + '_hp'] <= 0:
        bounty = random.randint(300, 700)
        user_balances[duel[curr]] = user_balances.get(duel[curr], 0) + bounty
        
        winner_char = duel[curr + '_char']
        photo_url = CHARACTER_PHOTOS.get(winner_char, CHARACTER_PHOTOS["Усопп"])
        
        try:
            bot.edit_message_text(
                chat_id=chat_id, message_id=duel['msg_id'],
                text=f"🏁 **Бой окончен! Победил {duel[curr+'_name']}!**"
            )
        except: pass
        
        win_text = (f"☠️ **БАУНТИ ХАНТ ЗАВЕРШЕН** ☠️\n"
                    f"━︎━︎━︎━︎━︎━︎━︎━︎━︎━︎━︎━︎\n"
                    f"💀 **{duel[opp+'_name']}** повержен на землю!\n\n"
                    f"🏆 Победитель: **{duel[curr+'_name']}** ({winner_char})\n"
                    f"💰 Награда за голову: **+{bounty} Белли** улетают на баланс!")
        
        bot.send_photo(chat_id, photo_url, caption=win_text, reply_markup=get_main_keyboard(), parse_mode="Markdown")
        
        del active_duels[chat_id]
        return

    # Передача хода
    duel['turn'] = duel[opp]
    duel['last_action_time'] = time.time()
    if action == "⚔️ Атака": duel[curr + '_status'] = 'normal'

    # Обновляем сообщение текущими HP
    try:
        bot.edit_message_text(
            chat_id=chat_id, message_id=duel['msg_id'],
            text=f"🏴‍☠️ **ИДЕТ БОЙ С ОХОТОЙ ЗА ГОЛОВАМИ** 🏴‍☠️\n\n"
                 f"👤 {duel['p1_name']} ({duel['p1_char']}) 🆚 👤 {duel['p2_name']} ({duel['p2_char']})\n"
                 f"━︎━︎━︎━︎━︎━︎━︎━︎━︎━︎━︎━︎\n"
                 f"❤️ {duel['p1_name']}: **{duel['p1_hp']} HP**\n"
                 f"❤️ {duel['p2_name']}: **{duel['p2_hp']} HP**\n\n"
                 f"💬 *{log_msg}*\n"
                 f"━︎━︎━︎━︎━︎━︎━︎━︎━︎━︎━︎━︎\n"
                 f"👉 Сейчас ход: **{duel[opp+'_name']}**! (Осталось {TURN_TIMEOUT} сек.)",
            reply_markup=get_battle_keyboard()
        )
    except: pass


if __name__ == '__main__':
    bot.infinity_polling()
