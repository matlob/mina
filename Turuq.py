import telebot
import sqlite3
import pandas as pd
from datetime import datetime
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

# إعداد البوت
TOKEN = "7084266510:AAECnhSvCW2nBSSfQTjY5CUMos3B40XXza0"
bot = telebot.TeleBot(TOKEN)

# إنشاء قاعدة بيانات لتخزين المستخدمين والمفاتيح السرية
conn = sqlite3.connect("bot_data.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        name TEXT,
        is_admin INTEGER,
        access_key TEXT
    )
""")
cursor.execute("""
    CREATE TABLE IF NOT EXISTS inventories (
        user_id INTEGER,
        company_name TEXT,
        item_name TEXT,
        sizes TEXT,
        counts TEXT,
        date TEXT
    )
""")
conn.commit()

# معرف الأدمن (قم بتغيير هذا إلى معرفك الخاص)
ADMIN_ID = 5695739834

def is_admin(user_id):
    return user_id == ADMIN_ID

def generate_keyboard(buttons):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for btn in buttons:
        keyboard.add(KeyboardButton(btn))
    return keyboard

# تخزين حالات المستخدمين
user_states = {}
user_data = {}

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    
    if user:
        bot.send_message(user_id, "Welcome back! Click below to start a new inventory.", reply_markup=generate_keyboard(["Create New Inventory"]))
    else:
        bot.send_message(user_id, "Do you have an access key?", reply_markup=generate_keyboard(["Yes", "No"]))
        user_states[user_id] = "awaiting_access_key_response"

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == "awaiting_access_key_response")
def handle_access_key_response(message):
    user_id = message.from_user.id
    if message.text == "Yes":
        bot.send_message(user_id, "Please enter your access key:")
        user_states[user_id] = "awaiting_access_key"
    else:
        bot.send_message(user_id, "Only users with an access key can use this bot.")

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == "awaiting_access_key")
def validate_access_key(message):
    user_id = message.from_user.id
    access_key = message.text
    cursor.execute("SELECT * FROM users WHERE access_key = ?", (access_key,))
    user = cursor.fetchone()
    
    if user:
        bot.send_message(user_id, "Access granted! Please enter your name:")
        user_states[user_id] = "awaiting_name"
        user_data[user_id] = {"access_key": access_key}
    else:
        bot.send_message(user_id, "Invalid key. Please try again.")

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == "awaiting_name")
def save_user_name(message):
    user_id = message.from_user.id
    name = message.text
    user_data[user_id]["name"] = name
    
    cursor.execute("INSERT INTO users (user_id, name, is_admin, access_key) VALUES (?, ?, 0, ?)",
                   (user_id, name, user_data[user_id]["access_key"]))
    conn.commit()
    
    bot.send_message(user_id, "Welcome to the company's bot!", reply_markup=generate_keyboard(["Create New Inventory"]))

@bot.message_handler(func=lambda message: message.text == "Create New Inventory")
def ask_company_name(message):
    user_id = message.from_user.id
    bot.send_message(user_id, "Please enter the company name:")
    user_states[user_id] = "awaiting_company_name"

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == "awaiting_company_name")
def save_company_name(message):
    user_id = message.from_user.id
    user_data[user_id] = {"company_name": message.text, "items": []}
    bot.send_message(user_id, "Enter all sizes (separate by comma):")
    user_states[user_id] = "awaiting_sizes"

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == "awaiting_sizes")
def save_sizes(message):
    user_id = message.from_user.id
    user_data[user_id]["sizes"] = message.text.split(",")
    bot.send_message(user_id, "Enter the item name:")
    user_states[user_id] = "awaiting_item_name"

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == "awaiting_item_name")
def save_item_name(message):
    user_id = message.from_user.id
    item_name = message.text
    user_data[user_id]["current_item"] = {"name": item_name, "counts": {}}
    bot.send_message(user_id, "Select a size:", reply_markup=generate_keyboard(user_data[user_id]["sizes"]))
    user_states[user_id] = "awaiting_size_selection"

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == "awaiting_size_selection")
def ask_quantity(message):
    user_id = message.from_user.id
    selected_size = message.text
    user_data[user_id]["current_item"]["current_size"] = selected_size
    bot.send_message(user_id, f"Enter quantity for size {selected_size}:")
    user_states[user_id] = "awaiting_quantity"

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == "awaiting_quantity")
def save_quantity(message):
    user_id = message.from_user.id
    quantity = message.text
    size = user_data[user_id]["current_item"]["current_size"]
    user_data[user_id]["current_item"]["counts"][size] = quantity
    bot.send_message(user_id, "Size recorded! Add more or finish?", reply_markup=generate_keyboard(["Add More", "Finish"]))
    user_states[user_id] = "awaiting_next_step"

# باقي الكود لإكمال الجرد وتصدير البيانات إلى Excel...