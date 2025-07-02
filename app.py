from flask import Flask, request
import telegram
from telebot.credentials import bot_token, bot_user_name, URL

global bot
global TOKEN
TOKEN = bot_token
bot = telegram.Bot(token=TOKEN)

# Start flask app
app = Flask(__name_)

# Respond when someone sends a message
@app.route('/{}'.format(TOKEN), methods=['POST'])
def respond():
    # Retrieve message in JSON then transform it to Telegram object
    update = telegram.Update.de_json(request.get_jason(force=True), bot)
    
    chat_id = update.message.chat.id
    msg_id = update.message.message_id
    
    # Encode text for unicode compatibility
    text = update.message.text.encode('utf-8').decode()
    
    # For debugging purposes
    print("Message received: ", text)
    
    # Display welcome message
    if text == "/start":
        bot_welcome = """
        Welcome to IncoLearn 👋! 
        This bot is developed by Allen James to help you with your studies. Let’s make studying easier, one message at a time!. Type /help to get started."
        """
        bot.sendMessage(chat_id=chat_id, text=bot_welcome, reply_to_message_id=msg_id)
        
    if text == "/help":
        bot_help = """
        Here is a list of the available commands:
        /start - Show a brief welcome message.
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
    else:
        try:
            # Replace non-letter/non-number characters with _ then store them to the variable
            text = re.sub(r"\W", "_", text)
            
            
        except Exception:
            bot.sendMessage(chat_id=chat_id, text="Invalid command. Please use /help to see a list of available commands.", reply_to_message_id=msg_id)
            
    return "ok"