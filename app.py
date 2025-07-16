"""
    Process for database transactions:
    1. Create connection
    2. Create cursor
    3. Create Query string
    4. Execute the query
    5. Commit to the query
    6. Close the cursor
    7. Close the connection
"""

import httpx
from fastapi import FastAPI, Request
from telebot.credentials import bot_token, bot_user_name, URL
import sqlite3
from telegram import Update
from cryptography.fernet import Fernet
import os
import smtplib

TOKEN = bot_token
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

client = httpx.AsyncClient()

app = FastAPI()    

# Generate a cypher key if file does not exist yet
file_path = "telebot/encryption_key.txt"
os.makedirs("telebot", exist_ok=True)

if not os.path.exists(file_path):
    key = Fernet.generate_key()
    with open(file_path, 'w') as file:
        file.write(key.decode())
    print("Encryption key generated and saved.")
else:
    print(f"The file '{file_path}' already exists.")

# Load the key and initialize cipher_suite
with open(file_path, 'r') as file:
    key = file.read().strip()

cipher_suite = Fernet(key.encode())

# Store user information asynchronously
async def store_user_data(username, first_name, last_name):
    # Encrypt the first and last name
    first_name_enc = cipher_suite.encrypt(first_name.encode())
    last_name_enc = cipher_suite.encrypt(last_name.encode())
    
    # Create database and cursor object from the cursor class
    os.makedirs("db", exist_ok=True) # Create folder if it does not exist
    connection = sqlite3.connect('db/incolearn.db')
    cur = connection.cursor()
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user(
            user_id INTEGER PRIMARY KEY AUTOINCREMENT, 
            username TEXT UNIQUE NOT NULL, 
            first_name TEXT NOT NULL, 
            last_name TEXT NOT NULL    
        )"""
    )
    print("Database created successfully!") # For debugging purposes
    # Commit the query and close the connection
    connection.commit()
    cur.close()
    connection.close()
    
    # Insert encrypted values if it does not exist yet
    try:
        connection = sqlite3.connect("db/incolearn.db")
        cur = connection.cursor()
        cur.execute("INSERT OR IGNORE INTO user (username, first_name, last_name) VALUES(?, ?, ?)", (username, first_name_enc, last_name_enc))
        print("User inserted successfully!") # For debugging
        # Commit the query and close the connection
        connection.commit()
        cur.close()
        connection.close()
 
    except sqlite3.IntegrityError:
        print("User already exists. Skipping insertion.")
        
    connection = sqlite3.connect("db/incolearn.db")
    cur = connection.cursor()
    cur.execute("SELECT * FROM user")
    rows = cur.fetchall()
    for row in rows:
        decrypted_row = (
            row[0],
            row[1],
            cipher_suite.decrypt(row[2]),
            cipher_suite.decrypt(row[3])
        )
        print(decrypted_row)
    
    # Commit the query and close the connection
    connection.commit()
    cur.close()
    connection.close()
 
@app.get("/")
async def root():
    return {"message": "Bot is running"}
        
        
@app.get("/setwebhook")
async def set_webhook():
    webhook_url = f"{URL}/webhook/"
    response = await client.get(
        f"{BASE_URL}/setWebhook",
        params={"url": webhook_url}
    )
    return response.json()
    
@app.post("/webhook/")
async def webhook(req: Request):
    data = await req.json()
    
    try:
        chat_id = data['message']['chat']['id']
        text = data['message']['text'].strip().lower()
    except KeyError:
        return{"ok": False, "error": "No valid message"}

    # Strip unecessary spaces and make it case-insensitive
    text = text.strip().lower()
    if text == "/help":
        bot_reply = """
        Here is a list of the available commands:
        /help - Show a list of all available commands.
        /newquiz <quiz name> - Start creating a new quiz.
        /addquestion <quiz name> - Add question to a quiz.
        /viewquizzes - Show a list of saved quizzes.
        /startquiz <quiz name> - Start answering a saved quiz.
        /editquiz <quiz name> - Modify an existing quiz.
        /deletequiz <quiz name> - Delete a quiz. This cannot be undone.
        /setreminder <quiz name> - Send a random question from an existing quiz every set time.
        /stopreminder - Stop the active /setreminder.
        /randomquestion <quiz name> - Instantly get a random question from the an existing quiz.
        /feedback <message> - Send feedback about the bot to the developer.
        """
        
    elif text.startswith("/newquiz"):
        # Obtain user information
        from_user = data["message"]["from"]
        sender_username = from_user.get("username") or "Not set"
        
        # Create a table if these is none yet
        connection = sqlite3.connect("db/incolearn.db")
        cursor = connection.cursor()
        cur.execute("""
                    CREATE TABLE IF NOT EXIST quiz(
                        quiz_id INTEGER PRIMARY KEY AUTOINCREMENT
                        user_id 
                    )
                    """)
    
    elif text == "/start":
        # Obtain user data then store it using a function
        from_user = data["message"]["from"]
        username = from_user.get("username") or "Not set"
        first_name = from_user.get("first_name") or "Not provided"
        last_name = from_user.get("last_name") or "Not provided"
        print(username, first_name, last_name) # For debugging
        await store_user_data(username, first_name, last_name)
        
        bot_reply = """
        Welcome to IncoLearn! To start creating your first quiz, type /newquiz. Type /help to view other available commands.
        """
        
    elif text.startswith("/feedback"):
        from_user = data["message"]["from"]
        sender_username = from_user.get("username") or "Not set"
        
        # Send an e-mail
        s = smtplib.SMTP('smtp.gmail.com', 587)
        s.starttls()
        s.login("allenjames.laxamana03@gmail.com", "wercpudbvmtjhewo")
        message = f"IncoLearn user feedback from username: {sender_username}\n\n{text.replace('/feedback', '').strip()}"
        print(message) # For debugging
        s.sendmail("allenjames.laxamana03@gmail.com", "allenjames.laxamana@gmail.com", message)
        s.quit()
        
        bot_reply = "Feedback sent to Allen James!"
        
    else:
        bot_reply = f"You said: {text}"
        
    await client.get(
        f"{BASE_URL}/sendMessage",
        params={"chat_id": chat_id, "text": bot_reply}
    )
            
    return{"ok": True}

