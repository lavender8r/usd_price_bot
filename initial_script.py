import os
import requests
import json
import telebot
import threading
import time
import logging
from requests.exceptions import RequestException, ReadTimeout, ConnectionError

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

API_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHANNEL_ID = '@lavender_test'
bot = telebot.TeleBot(API_TOKEN)

NOBITEX_URL = 'https://api.nobitex.ir/market/stats'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:132.0) Gecko/20100101 Firefox/132.0',
    'Accept': 'application/json',
    'Origin': 'https://nobitex.ir'
}

interval = 60
running = False
last_price = None

def get_usd_rate():
    try:
        response = requests.get(f"{NOBITEX_URL}?srcCurrency=usdt", headers=HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()
        latest_value = int(data['stats']['usdt-rls']['latest'])/10
        rounded_price = round(latest_value / 50) * 50
        return rounded_price
    except (RequestException, json.JSONDecodeError) as e:
        logging.error(f"Failed to fetch exchange rate: {e}")
        return None

def send_to_channel():
    global running, last_price
    while running:
        try:
            usd_price = get_usd_rate()
            if usd_price and usd_price != last_price:
                emoji = '🔺' if last_price and usd_price > last_price else '🔽' if last_price else ''
                bot.send_message(CHANNEL_ID, f"USD Price: {usd_price} {emoji}")
                last_price = usd_price
            else:
                logging.info("Price unchanged; no message sent.")
            time.sleep(interval)
        except Exception as e:
            logging.error(f"Error in send_to_channel: {e}")
            time.sleep(10)

@bot.message_handler(commands=['channel'])
def start_sending(message):
    if message.from_user.id == 86681263:
        global running
        if not running:
            running = True
            threading.Thread(target=send_to_channel, daemon=True).start()
            bot.reply_to(message, f"Started sending updates every {interval} seconds.")
        else:
            bot.reply_to(message, "Updates are already running.")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Hi! Use /price to get the latest exchange rate.")

@bot.message_handler(commands=['stop'])
def stop_sending(message):
    if message.from_user.id == 86681263:
        global running
        running = False
        bot.reply_to(message, "Stopped sending updates.")

@bot.message_handler(commands=['price'])
def send_price(message):
    usd_price = get_usd_rate()
    if usd_price:
        bot.reply_to(message, f"USD Price: {usd_price}")
    else:
        bot.reply_to(message, "Failed to fetch exchange rate.")

def start_bot():
    while True:
        global running
        if not running:
            running = True
            threading.Thread(target=send_to_channel, daemon=True).start()
        try:
            bot.polling(non_stop=True, interval=1)
        except ReadTimeout:
            logging.warning("Polling timeout. Retrying...")
            time.sleep(10)
        except ConnectionError:
            logging.error("Connection error. Retrying...")
            time.sleep(10)
        except Exception as e:
            logging.critical(f"Unexpected error: {e}. Restarting bot...")
            time.sleep(10)

if __name__ == '__main__':
    start_bot()
