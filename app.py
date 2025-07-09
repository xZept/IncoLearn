from flask import Flask, request
import telegram
from telebot.credentials import bot_token, bot_user_name, URL
import asyncio
from telegram.request import HTTPXRequest

global bot
global TOKEN
TOKEN = bot_token

# Increase connection pool size
trequest = HTTPXRequest(connection_pool_size=20)
bot = telegram.Bot(token=TOKEN, request=trequest)

# Start flask app
app = Flask(__name__)
    
# Respond when someone sends a message
@app.route('/8074096606:AAEUzypSnMyVarj4bb3NA0jU0rSFqeHjCAc', methods=['POST'])
def respond():
    # Retrieve message in JSON then transform it to Telegram object
    update = telegram.Update.de_json(request.get_json(force=True), bot)
    
    chat_id = update.message.chat.id
    msg_id = update.message.message_id
    text = update.message.text
    
    # For debugging purposes
    print("Message received: ", text)
    
        
    # Strip unecessary spaces and make it case-insensitive
    text = text.strip().lower()
    if text == "/help":
        bot_help = """
        Here is a list of the available commands:
        /help - Show a list of all available commands.
        /newquiz = Start creating a new quiz.
        /addquestion <question> = Add question to a quiz.
        /viewquizzes - Show a list of saved quizzes.
        /startquiz <quiz name> - Start answering a saved quiz.
        /editquiz <quiz name> - Modify an existing quiz.
        /deletequiz <quiz name> - Delete a quiz. This cannot be undone.
        /setreminder <quiz name> - Send a random question from an existing quiz every set time.
        /stopreminder - Stop the active /setreminder.
        /randomquestion <quiz name> - Instantly get a random question from the an existing quiz.
        /feedback - Send feedback about the bot to the developer.
        """
        try:
            loop = asyncio.get_event_loop()
            loop.create_task(bot.sendMessage(chat_id=chat_id, text=bot_help, reply_to_message_id=msg_id))
        except telegram.error.BadRequest:
            # Fall back action in case the message cannot be found
            loop = asyncio.get_event_loop()
            loop.create_task(bot.sendMessage(chat_id=chat_id, text=bot_help))

        
    else:
        try:
            # Put bot command logic here
            if text == "/newquiz":
                print("sample")
            
        except Exception:
            bot.sendMessage(chat_id=chat_id, text="Invalid command. Please use /help to see a list of available commands.", reply_to_message_id=msg_id)
            
    return "ok"

# Set webhook
@app.route('/setwebhook', methods=['GET', 'POST'])
def set_webhook():
    s = bot.setWebhook('{URL}{HOOK}'.format(URL=URL, HOOK=TOKEN))
    if s:
        return "webhook setup ok"
    else:
        return "webhook setup failed"
    
# Setup flask app
@app.route('/')
def index():
    return "Bot is running"

# Line commented out to let Gunicorn run the app
# if __name__ == "__main__":
#     app.run(threaded=True) # Enable threading to allow multiple users to use the bot at the same time
