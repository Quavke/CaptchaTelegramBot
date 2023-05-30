import conf
import telebot
from telebot import types
from captcha.image import ImageCaptcha
from random import choice
import os
import sqlite3

id_ = ''
key = ''
tglink = ''
botlink = ''
num_cap = 4
db = sqlite3.connect('table.db')
cur = db.cursor()
cur.execute("""CREATE TABLE IF NOT EXISTS users (idt TEXT, key TEXT, tglink TEXT)""")

telegram_api = conf.telegram
bot = telebot.TeleBot(telegram_api)


def captcha_gen():
    a_captcha = list("abcdefghijklmnopqrstuvwxyz?!0123456789")
    pattern = []

    for i in range(7):
        pattern.append(choice(a_captcha))

    imagecaptcha = ImageCaptcha(width=300, height=200)

    captcha_filename = 'captcha.png'

    # Check if the file exists and delete it
    if os.path.exists(captcha_filename):
        os.remove(captcha_filename)

    imagecaptcha.write(pattern, captcha_filename)
    string = ''.join(pattern)

    with open(captcha_filename, 'rb') as file:
        captcha_content = file.read()

    os.remove(captcha_filename)

    return captcha_content, string


def key_gen():
    a = list("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ&?!-+0123456789")
    gen_key = []
    for i in range(20):
        gen_key.append(choice(a))
    string = ''.join(gen_key)
    return string


def generate_back_button():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton('⬅️ Назад'))
    return markup


@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, 'Привет! Это бот для проверки на робота🤖\nВы можете посмотреть все возможные действия в меню!📋')

def back(message):
    bot.send_message(message.chat.id, 'Вы вернулись назад!↩️\nВы можете посмотреть все возможные действия в меню!📋')


@bot.message_handler(commands=['new_key'])
def new_key(message):
    global id_
    id_ = message.from_user.id
    bot.send_message(message.chat.id, 'Отправьте ссылку на ваш телеграм канал📢', reply_markup=generate_back_button())
    bot.register_next_step_handler(message, check_tg)


def check_tg(message):
    if message.text == '⬅️ Назад':
        back(message)
        return

    tglink = message.text
    if 'https://t.me/' in tglink:
        db = sqlite3.connect('table.db')
        cur = db.cursor()
        
        # Генерация уникального ключа
        string = key_gen()
        while True:
            # Проверка наличия ключа в базе данных
            cur.execute("SELECT COUNT(*) FROM users WHERE key = ?", (string,))
            result = cur.fetchone()[0]
            if result == 0:
                break
            else:
                string = key_gen()
        
        cur.execute("SELECT tglink FROM users WHERE tglink = ? AND idt = ?", (tglink, message.from_user.id,))
        tg_check = cur.fetchall()
        if tg_check:
            cur.execute("UPDATE users SET key = ? WHERE tglink = ? AND idt = ?", (string, tglink, message.from_user.id,))
            db.commit()
            db.close()
            bot.send_message(message.chat.id, f'Ваш новый ключ: `{string}`🔑🔁🗝', parse_mode="Markdown")
        else:
            cur.execute("INSERT INTO users(idt, key, tglink) VALUES(?, ?, ?)", (message.from_user.id, string, tglink,))
            db.commit()
            db.close()
            bot.send_message(message.chat.id, f'Ваш ключ: `{string}`🔑', parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, 'Некорректная ссылка❌')


@bot.message_handler(commands=['key'])
def key(message):
    global num_cap
    bot.send_message(message.chat.id, 'Введите ключ🔑', reply_markup=generate_back_button())
    num_cap = 4
    bot.register_next_step_handler(message, check_key)


def check_key(message):
    if message.text == '⬅️ Назад':
        back(message)
        return

    global tglink, param
    key = message.text
    db = sqlite3.connect('table.db')
    cur = db.cursor()
    cur.execute("SELECT tglink FROM users WHERE key = ?", (key,))
    tglinkdb = cur.fetchone()
    if tglinkdb:
        tglink = tglinkdb[0]
        captcha_im, param = captcha_gen()
        markup = types.InlineKeyboardMarkup(row_width=2)
        btn1 = types.InlineKeyboardButton('🔄', callback_data='regenerate')
        btn2 = types.InlineKeyboardButton('⬅️ Назад', callback_data='back')
        markup.add(btn1, btn2)
        bot.send_photo(chat_id=message.chat.id, photo=captcha_im, caption='Введите текст с картинки🖼', reply_markup=markup)
        bot.register_next_step_handler(message, captcha_check)
    else:
        bot.send_message(message.chat.id, 'Такого ключа не существует🤷‍♂️ попробуйте ещё раз /key🔒')
    db.close()


@bot.callback_query_handler(func=lambda callback: True)
def regen(callback):
    global param, num_cap
    num_cap = 4
    if callback.data == 'regenerate':
        captcha_im, param = captcha_gen()
        markup = types.InlineKeyboardMarkup(row_width=2)
        btn1 = types.InlineKeyboardButton('🔄', callback_data='regenerate')
        btn2 = types.InlineKeyboardButton('⬅️ Назад', callback_data='back')
        markup.add(btn1, btn2)
        bot.send_photo(chat_id=callback.message.chat.id, photo=captcha_im, caption='Введите текст с картинки🖼', reply_markup=markup)
    elif callback.data == 'back':
        back(callback.message)
        bot.clear_step_handler_by_chat_id(callback.message.chat.id)
        return

def captcha_check(message):
    global param, tglink, num_cap
    num_cap -= 1
    if message.text == param:
        bot.send_message(message.chat.id, f'Ваша ссылка: {tglink} 🔓')
        tglink = ''
    else:
        if num_cap > 0:
            if num_cap > 1:
                string = 'попытки❗️'
            else:
                string = 'попытка‼️'
            bot.send_message(message.chat.id, f'Неправильно❌ У вас ещё есть {num_cap} {string}')
            bot.register_next_step_handler(message, captcha_check)
        else:
            bot.send_message(message.chat.id, 'У вас закончились попытки😕 Попробуйте ещё раз /key🔒')
            num_cap = 4


@bot.message_handler(commands=['my_keys'])
def my_keys(message):
    user_id = message.from_user.id

    db = sqlite3.connect('table.db')
    cur = db.cursor()

    cur.execute("SELECT tglink, key FROM users WHERE idt = ?", (user_id,))
    results = cur.fetchall()

    if results:
        response = "Ваши ключи🔐:\n"
        for tglink, key in results:
            response += f"{tglink} - `{key}`\n"
        bot.send_message(message.chat.id, response, parse_mode="Markdown")

    else:
        bot.send_message(message.chat.id, "У вас нет сохраненных ключей🔐")

    db.close()


@bot.message_handler(commands=['delete_key'])
def delete_key(message):
    bot.send_message(message.chat.id, 'Пожалуйста, отправьте мне ссылку на телеграм канал или ключ от него🗑',reply_markup=generate_back_button())
    bot.register_next_step_handler(message, delete)


def delete(message):
    if message.text == '⬅️ Назад':
        back(message)
        return

    mess = message.text
    db = sqlite3.connect('table.db')
    cur = db.cursor()
    if 'https://t.me/' in mess:
        cur.execute("SELECT tglink FROM users WHERE tglink = ? AND idt = ?", (mess, message.from_user.id,))
        res = cur.fetchall()
        if res:
            cur.execute("DELETE FROM users WHERE tglink = ? AND idt = ?", (mess, message.from_user.id,))
            db.commit()
            bot.send_message(message.chat.id, 'Ключ успешно удалён✅')
        else:
            bot.send_message(message.chat.id, 'У вас нет такой ссылки🤷‍♂️')
    else:
        cur.execute("SELECT tglink FROM users WHERE key = ? AND idt = ?", (mess, message.from_user.id,))
        res = cur.fetchall()
        if res:
            cur.execute("DELETE FROM users WHERE key = ? AND idt = ?", (mess, message.from_user.id,))
            db.commit()
            bot.send_message(message.chat.id, 'Ключ успешно удалён✅')
        else:
            bot.send_message(message.chat.id, 'У вас нет такого ключа🤷‍♂️')
    db.close()


def generate_back_button():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton('⬅️ Назад'))
    return markup

@bot.message_handler(commands=['help'])
def help(message):
    bot.send_message(message.chat.id, 'Этот текст должен помочь тебе с использованием бота🤖\n1. /new_key - это команда для создания ключа, по нему другие пользователи смогут получить ссылку на ваш телеграм канал, которую бот попросит ввести при выполнении. <b>Важно помнить, что несколько пользователей могут создавать ключи на один и тот же тгк, но они будут индивидуальные</b>\n2. /key - эта команда нужна, чтобы пользователи могли ввести ключ. Пользователь отправляет ключ, получает каптчу, проходит её и вуаля! Бот выдаёт ссылку, которая зарегистрирована на ключ.\n3. /my_keys - эта команда нужна для показа всех ключей и ссылок зарегистрированных на эти ключи. <b>Команда показывает только те ключи, что были зарегистрированы вами.</b>\n4./delete_key - команда, которая удаляет ключ по ссылке/ключу привязанному к ней. <b>Команда удаляет только ваш ключ. Вы не можете удалить чужой ключ по ссылке/ключу</b>\n\nНадеюсь, это вам помогло😄', parse_mode='html')



dibil_num = 0


@bot.message_handler()
def defender(message):
    global dibil_num
    if dibil_num < 3:
        bot.send_message(message.chat.id, 'Сам такой🗣fsdfssdas')
        dibil_num += 1
    else:
        bot.send_message(message.chat.id, 'Там внизу меню, идиот')
        dibil_num = 0


bot.polling()
