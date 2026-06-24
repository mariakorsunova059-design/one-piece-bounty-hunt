# ==========================================
# ТОКЕН ВСТАВЛЯТЬ СЮДА:
TOKEN = '8777992778:AAE-yWMJpVvqaIPT-qh4lGGUNqtIcDAlIxI'
# ==========================================

import telebot
from telebot import types
import random
from flask import Flask
from threading import Thread
import os

bot = telebot.TeleBot(TOKEN)

# --- МИНИ ВЕБ-СЕРВЕР ДЛЯ RENDER ---
# Он нужен только для того, чтобы Render не отключал бота из-за отсутствия порта
app = Flask('')

@app.route('/')
def home():
    return "Бот One Piece запущен и работает!"

def run_flask():
    # Render автоматически передает порт в переменные окружения
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.start()


# --- БАЗА ДАННЫХ В ПАМЯТИ ---
user_characters = {}
active_duels = {}


# --- КЛАВИАТУРЫ ---
def get_start_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton("🎯 Выбрать Усоппа (Старт)"))
    return markup

def get_battle_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_attack = types.KeyboardButton("⚔️ Атака")
    btn_def = types.KeyboardButton("🛡️ Защита")
    btn_spec = types.KeyboardButton("✨ Особая способность (Заблокировано)")
    markup.row(btn_attack, btn_def)
    markup.add(btn_spec)
    return markup


# --- ЛОГИКА БОТА ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    if message.chat.type == 'private':
        bot.reply_to(message, 
                     "Привет, пират! Добро пожаловать в мир One Piece Bounty Hunt!\n"
                     "Чтобы начать охоту за головами, выбери своего стартового персонажа ниже:", 
                     reply_markup=get_start_keyboard())
    else:
        bot.reply_to(message, "Йо-хо-хо! Добавьте меня в чат и напишите кому-то в ответ 'баунти хант', чтобы начать дуэль!")

@bot.message_handler(func=lambda m: m.text == "🎯 Выбрать Усоппа (Старт)")
def choose_usopp(message):
    user_characters[message.from_user.id] = "Усопп"
    bot.reply_to(message, "🎯 Ты выбрал Усоппа! Теперь ты можешь драться в чатах!")

@bot.message_handler(func=lambda m: m.text and m.text.lower() == "баунти хант")
def start_bounty_hunt(message):
    if message.chat.type == 'private':
        bot.reply_to(message, "Эту команду нужно писать в чате в ответ на сообщение соперника!")
        return
    
    if not message.reply_to_message:
        bot.reply_to(message, "Эй! Напиши 'баунти хант' в ответ на сообщение того, на кого хочешь напасть!")
        return

    p1_id = message.from_user.id
    p2_id = message.reply_to_message.from_user.id
    p1_name = message.from_user.first_name
    p2_name = message.reply_to_message.from_user.first_name

    if p1_id == p2_id:
        bot.reply_to(message, "Ты не можешь объявить награду за собственную голову!")
        return

    if p1_id not in user_characters:
        bot.reply_to(message, f"❌ {p1_name}, сначала зайди ко мне в ЛС и выбери персонажа через /start!")
        return
    if p2_id not in user_characters:
        bot.reply_to(message, f"❌ {p2_name} еще не выбрал персонажа. Ему нужно зайти ко мне в ЛС и нажать /start!")
        return

    chat_id = message.chat.id
    if chat_id in active_duels:
        bot.reply_to(message, "В этом чате уже идет одна битва! Подождите ее окончания.")
        return

    fighters = [p1_id, p2_id]
    first_turn = random.choice(fighters)
    first_name = p1_name if first_turn == p1_id else p2_name

    active_duels[chat_id] = {
        'p1': p1_id, 'p1_name': p1_name, 'p1_char': user_characters[p1_id], 'p1_hp': 100, 'p1_status': 'normal',
        'p2': p2_id, 'p2_name': p2_name, 'p2_char': user_characters[p2_id], 'p2_hp': 100, 'p2_status': 'normal',
        'turn': first_turn
    }

    bot.send_message(chat_id, 
                     f"🏴‍☠️ **БАУНТИ ХАНТ НАЧАТ!** 🏴‍☠️\n\n"
                     f"👤 {p1_name} ({user_characters[p1_id]}) 🆚 👤 {p2_name} ({user_characters[p2_id]})\n\n"
                     f"🎲 Кубики брошены... Первым атакует **{first_name}**!", 
                     reply_markup=get_battle_keyboard(), parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text in ["⚔️ Атака", "🛡️ Защита"])
def handle_battle_turn(message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if chat_id not in active_duels:
        return

    duel = active_duels[chat_id]

    if user_id != duel['turn']:
        return

    if user_id == duel['p1']:
        curr, opp = 'p1', 'p2'
    else:
        curr, opp = 'p2', 'p1'

    action = message.text
    log_msg = ""

    if action == "🛡️ Защита":
        duel[curr + '_status'] = 'defending'
        log_msg = f"🛡️ **{duel[curr+'_name']}** ({duel[curr+'_char']}) встает в защитную стойку!"
    
    elif action == "⚔️ Атака":
        damage = random.randint(15, 25)
        if duel[opp + '_status'] == 'defending':
            damage = int(damage * 0.3)
            duel[opp + '_status'] = 'normal'
            log_msg = f"⚔️ **{duel[curr+'_name']}** атакует, но **{duel[opp+'_name']}** заблокировал удар! Нанесено {damage} урона.\n"
        else:
            log_msg = f"⚔️ **{duel[curr+'_name']}** наносит мощный удар! Нанесено {damage} урона.\n"
        
        duel[opp + '_hp'] -= damage
        if duel[opp + '_hp'] < 0:
            duel[opp + '_hp'] = 0

    if duel[opp + '_hp'] <= 0:
        bounty = random.randint(500000, 2000000)
        bot.send_message(chat_id, 
                         f"{log_msg}\n\n"
                         f"💀 **{duel[opp+'_name']}** повержен!\n"
                         f"🏆 Победитель: **{duel[curr+'_name']}**!\n"
                         f"💰 Твоя награда увеличилась на **{bounty:,}** Белли!", 
                         reply_markup=types.ReplyKeyboardRemove())
        del active_duels[chat_id]
        return

    duel['turn'] = duel[opp]
    if action == "⚔️ Атака":
        duel[curr + '_status'] = 'normal'

    status_report = (
        f"{log_msg}\n\n"
        f"📊 **Состояние бойцов:**\n"
        f"❤️ {duel['p1_name']}: {duel['p1_hp']} HP\n"
        f"❤️ {duel['p2_name']}: {duel['p2_hp']} HP\n\n"
        f"👉 Ход переходит к **{duel[opp+'_name']}**!"
    )
    bot.send_message(chat_id, status_report, reply_markup=get_battle_keyboard())


# --- ЗАПУСК ---
if __name__ == '__main__':
    # Сначала запускаем веб-сервер пинга
    keep_alive()
    print("Веб-сервер пинга запущен.")
    
    # Затем запускаем самого бота
    print("Бот One Piece успешно запущен!")
    bot.infinity_polling()
