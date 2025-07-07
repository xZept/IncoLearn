from flask import Flask, request
import telegram
from telebot.credentials import bot_token, bot_user_name, URL
 
global bot
global TOKEN
TOKEN = bot_token
bot = telegram.Bot(token=TOKEN)

# Start flask app
app = Flask(__name__)
    
# Respond when someone sends a message
@app.route('/{}'.format(TOKEN), methods=['POST'])
def respond():
    # Retrieve message in JSON then transform it to Telegram object
    update = telegram.Update.de_json(request.get_json(force=True), bot)
    
    chat_id = update.message.chat.id
    msg_id = update.message.message_id
    
    # Encode text for unicode compatibility
    text = update.message.text.encode('utf-8').decode()
    
    # For debugging purposes
    print("Message received: ", text)
    
        
    if text == "/help":
        bot_help = """
        Here is a list of the available commands:
        /help - Show a list of all available commands.
        /newquiz <quiz name> = Start creating a new quiz.
        /addquestion <quiz name> = Add question to a quiz.
        /viewquizzes - Show a list of saved quizzes.
        /viewquiz <quiz name> - Show the list of questions from a chosen quiz.
        /startquiz <quiz name> - Start answering a saved quiz.
        /editquiz <quiz name> - Modify an existing quiz.
        /deletequiz <quiz name> - Delete a quiz. This cannot be undone.
        /setreminder <quiz name> - Send a random question from an existing quiz every set time.
        /stopreminder - Stop the active /setreminder.
        /randomquestion <quiz name> - Instantly get a random question from the an existing quiz.
        /feedback - Send feedback about the bot to the developer.
        """
        bot.sendMessage(chat_id=chat_id, text=bot_help, reply_to_message_id=msg_id)
        
        # For debugging purposes
        print("Message received: ", text)
        
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


# if __name__ == "__main__":
#     app.run(threaded=True) # Enable threading to allow multiple users to use the bot at the same time
