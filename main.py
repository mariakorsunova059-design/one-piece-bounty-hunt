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
user_characters = {}  # ID пользователя -> Имя персонажа
user_balances = {}    # ID пользователя -> Баланс Белли
user_inventory = {}   # ID пользователя -> Список купленных персонажей (например, ["Усопп", "Зоро"])
last_spin = {}        # ID пользователя -> UNIX-время последнего прокрута рулетки
active_duels = {}     # Chat_ID -> Данные текущего боя

# Лимит для рулетки: 2 часа в секундах (2 * 60 * 60)
ROULETTE_COOLDOWN = 7200 
# Время на ход в секундах (например, 1 минута). Если за это время игрок не походил — он проиграл по таймауту.
TURN_TIMEOUT = 60
# Штраф за бездействие (в Белли)
TIMEOUT_PENALTY = 500

# --- МИНИ ВЕБ-СЕРВЕР ДЛЯ RENDER ---
app = Flask('')
@app.route('/')
def home(): return "Бот Bounty Hunt запущен!"
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


# --- ФУНКЦИЯ ПРОВЕРКИ ТАЙМАУТА ХОДА ---
def check_duel_timeout(chat_id):
    """Проверяет, не истекло ли время на ход. Если истекло, завершает бой со штрафом."""
    if chat_id not in active_duels:
        return False
        
    duel = active_duels[chat_id]
    current_time = time.time()
    
    if current_time - duel['last_action_time'] > TURN_TIMEOUT:
        # Определяем, кто виноват (чей сейчас был ход)
        loser_id = duel['turn']
        if loser_id == duel['p1']:
            loser_name = duel['p1_name']
            winner_name = duel['p2_name']
        else:
            loser_name = duel['p2_name']
            winner_name = duel['p1_name']
            
        # Снимаем штраф с виновника
        user_balances[loser_id] = max(0, user_balances.get(loser_id, 0) - TIMEOUT_PENALTY)
        
        bot.send_message(chat_id, 
                         f"⏱ **ВРЕМЯ ИСТЕКЛО!**\n\n"
                         f"💀 Игрок **{loser_name}** слишком долго думал и исключен из боя за бездействие!\n"
                         f"🏆 Победитель: **{winner_name}**\n"
                         f"💸 С баланса {loser_name} списано **{TIMEOUT_PENALTY} Белли** штрафа.",
                         reply_markup=types.ReplyKeyboardRemove())
                         
        del active_duels[chat_id]
        return True
    return False


# --- КОМАНДА /START ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    uid = message.from_user.id
    # Выдаем стартового Усоппа бесплатно, если у игрока еще вообще никого нет
    if uid not in user_inventory:
        user_inventory[uid] = ["Усопп"]
    if uid not in user_characters:
        user_characters[uid] = "Усопп"
        
    bot.reply_to(message, 
                 "🏴‍☠️ Добро пожаловать в мир One Piece Bounty Hunt!\n"
                 "Здесь ты можешь крутить рулетку, покупать персонажей и устраивать дуэли в чатах.", 
                 reply_markup=get_main_keyboard())


# --- РУЛЕТКА (РАЗ В 2 ЧАСА) ---
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

    # Логика шансов: 100(40%), 300(30%), 500(20%), 700(7.5%), 1000(2.5%)
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


# --- МАГАЗИН И ПЕРСОНАЖИ ---
@bot.message_handler(func=lambda m: m.text == "🎯 Персонажи / Магазин")
def show_shop(message):
    uid = message.from_user.id
    if uid not in user_inventory:
        user_inventory[uid] = ["Усопп"]
        
    bal = user_balances.get(uid, 0)
    current_char = user_characters.get(uid, "Не выбран")
    
    text = (f"👤 **Твой текущий боец:** {current_char}\n"
            f"💰 Твой баланс: {bal} Белли\n\n"
            f"🛒 **Доступные персонажи:**\n"
            f"1. **Усопп** — Бесплатно (Стартовый)\n"
            f"2. **Зоро** — 300 Белли\n\n"
            f"Чтобы купить или выбрать персонажа, используй кнопки ниже:")
            
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    # Кнопка для Усоппа
    markup.add(types.InlineKeyboardButton("🎯 Выбрать Усоппа", callback_data="set_Усопп"))
    
    # Кнопка для Зоро (динамическая: купить или выбрать)
    if "Зоро" in user_inventory[uid]:
        markup.add(types.InlineKeyboardButton("⚔️ Выбрать Зоро", callback_data="set_Зоро"))
    else:
        markup.add(types.InlineKeyboardButton("🟢 Купить Зоро (300 Белли)", callback_data="buy_Зоро"))
        
    bot.reply_to(message, text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: True)
def handle_shop_buttons(call):
    uid = call.from_user.id
    action = call.data
    
    if uid not in user_inventory:
        user_inventory[uid] = ["Усопп"]

    if action.startswith("set_"):
        char_name = action.split("_")[1]
        user_characters[uid] = char_name
        bot.answer_callback_query(call.id, f"Ты выбрал персонажа: {char_name}!")
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=f"✅ Успешно выбран персонаж: **{char_name}**!")
        
    elif action == "buy_Зоро":
        bal = user_balances.get(uid, 0)
        if bal >= 300:
            user_balances[uid] = bal - 300
            user_inventory[uid].append("Зоро")
            user_characters[uid] = "Зоро"
            bot.answer_callback_query(call.id, "🎉 Успешная покупка! Ророноа Зоро присодинился к твоей команде!")
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="⚔️ Ты купил и выбрал **Зоро**!")
        else:
            bot.answer_callback_query(call.id, "❌ Недостаточно Белли! Скрути рулетку.", show_alert=True)


# --- ПРОФИЛЬ ---
@bot.message_handler(func=lambda m: m.text == "📊 Мой профиль")
def show_profile(message):
    uid = message.from_user.id
    char = user_characters.get(uid, "Усопп")
    bal = user_balances.get(uid, 0)
    inv = ", ".join(user_inventory.get(uid, ["Усопп"]))
    bot.reply_to(message, f"📋 **ПРОФИЛЬ ПИРАТА:**\n\n👤 Активный боец: *{char}*\n💰 Баланс: *{bal} Белли*\n🎒 Твоя команда: *{inv}*", parse_mode="Markdown")


# --- ЛОГИКА БОЯ С ТАЙМАУТОМ ---
@bot.message_handler(func=lambda m: m.text and m.text.lower() == "баунти хант")
def start_bounty_hunt(message):
    if message.chat.type == 'private':
        bot.reply_to(message, "Эту команду нужно писать в чате в ответ на сообщение соперника!")
        return
    if not message.reply_to_message:
        bot.reply_to(message, "Напиши 'баунти хант' в ответ на сообщение того, на кого хочешь напасть!")
        return

    p1_id, p2_id = message.from_user.id, message.reply_to_message.from_user.id
    p1_name, p2_name = message.from_user.first_name, message.reply_to_message.from_user.first_name

    if p1_id == p2_id:
        bot.reply_to(message, "Нельзя нападать на самого себя!")
        return

    p1_char = user_characters.get(p1_id, "Усопп")
    p2_char = user_characters.get(p2_id, "Усопп")

    chat_id = message.chat.id
    
    # Если в чате уже идет бой, сначала проверяем, не завис ли он по таймауту
    if chat_id in active_duels:
        if not check_duel_timeout(chat_id):
            bot.reply_to(message, "В этом чате уже идет битва! Подождите ее окончания или пока истечет время на ход.")
            return
        else:
            # Если старый бой закрылся по таймауту, разрешаем начать новый
            pass

    fighters = [p1_id, p2_id]
    first_turn = random.choice(fighters)
    first_name = p1_name if first_turn == p1_id else p2_name

    active_duels[chat_id] = {
        'p1': p1_id, 'p1_name': p1_name, 'p1_char': p1_char, 'p1_hp': 100, 'p1_status': 'normal',
        'p2': p2_id, 'p2_name': p2_name, 'p2_char': p2_char, 'p2_hp': 100, 'p2_status': 'normal',
        'turn': first_turn,
        'last_action_time': time.time()  # Фиксируем время старта хода
    }

    bot.send_message(chat_id, 
                     f"🏴‍☠️ **БАУНТИ ХАНТ НАЧАТ!** 🏴‍☠️\n\n"
                     f"👤 {p1_name} ({p1_char}) 🆚 👤 {p2_name} ({p2_char})\n\n"
                     f"🎲 Первым атакует **{first_name}**!\n⏱ У вас есть **{TURN_TIMEOUT} сек.** на ход, иначе — штраф!", 
                     reply_markup=get_battle_keyboard())


@bot.message_handler(func=lambda m: m.text in ["⚔️ Атака", "🛡️ Защита"])
def handle_battle_turn(message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if chat_id not in active_duels:
        return

    # Сначала проверяем: может, время на ход уже вышло до того, как кнопка была нажата?
    if check_duel_timeout(chat_id):
        return

    duel = active_duels[chat_id]

    if user_id != duel['turn']:
        return

    if user_id == duel['p1']: curr, opp = 'p1', 'p2'
    else: curr, opp = 'p2', 'p1'

    action = message.text
    log_msg = ""

    if action == "🛡️ Защита":
        duel[curr + '_status'] = 'defending'
        log_msg = f"🛡️ **{duel[curr+'_name']}** ({duel[curr+'_char']}) встает в блок!"
    elif action == "⚔️ Атака":
        # Урон Зоро чуть выше, так как он платный персонаж (для баланса)
        min_dmg, max_dmg = (18, 28) if duel[curr+'_char'] == "Зоро" else (15, 25)
        damage = random.randint(min_dmg, max_dmg)
        
        if duel[opp + '_status'] == 'defending':
            damage = int(damage * 0.3)
            duel[opp + '_status'] = 'normal'
            log_msg = f"⚔️ **{duel[curr+'_name']}** бьет, но соперник заблокировал удар! Нанесено {damage} урона."
        else:
            log_msg = f"⚔️ **{duel[curr+'_name']}** наносит удар! Нанесено {damage} урона."
        
        duel[opp + '_hp'] = max(0, duel[opp + '_hp'] - damage)

    # Проверка на конец боя
    if duel[opp + '_hp'] <= 0:
        bounty = random.randint(300, 700) # Награда Белли за победу
        user_balances[duel[curr]] = user_balances.get(duel[curr], 0) + bounty
        bot.send_message(chat_id, 
                         f"{log_msg}\n\n"
                         f"💀 **{duel[opp+'_name']}** повержен!\n"
                         f"🏆 Победитель: **{duel[curr+'_name']}**!\n"
                         f"💰 Получено в награду: **{bounty} Белли**!", 
                         reply_markup=types.ReplyKeyboardRemove())
        del active_duels[chat_id]
        return

    # Передача хода
    duel['turn'] = duel[opp]
    duel['last_action_time'] = time.time() # ОБНУЛЯЕМ ТАЙМЕР ДЛЯ СЛЕДУЮЩЕГО ИГРОКА
    if action == "⚔️ Атака": duel[curr + '_status'] = 'normal'

    status_report = (
        f"{log_msg}\n\n"
        f"📊 **HP бойцов:**\n"
        f"❤️ {duel['p1_name']}: {duel['p1_hp']} HP\n"
        f"❤️ {duel['p2_name']}: {duel['p2_hp']} HP\n\n"
        f"👉 Следующий ход: **{duel[opp+'_name']}**! У тебя {TURN_TIMEOUT} секунд!"
    )
    bot.send_message(chat_id, status_report, reply_markup=get_battle_keyboard())


# Функция для автоматической очистки зависших боев, если игроки просто забыли про бота
@bot.message_handler(commands=['check_battle'])
def manual_timeout_check(message):
    chat_id = message.chat.id
    if chat_id in active_duels:
        if not check_duel_timeout(chat_id):
            bot.reply_to(message, "Время на ход еще не вышло.")
    else:
        bot.reply_to(message, "В этом чате сейчас нет активных дуэлей.")


if __name__ == '__main__':
    bot.infinity_polling()
