from flask import Flask, request
import telegram
from telebot.credentials import bot_token, bot_user_name, URL

global bot
global TOKEN
TOKEN = bot_token
bot = telegram.Bot(token=TOKEN)

# Start flask app
app = Flask(__name_)
@app.route('/{}'.format(TOKEN), methods=['POST'])