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
import os
import smtplib
import io

TOKEN = bot_token
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

client = httpx.AsyncClient()

app = FastAPI()    

# Global variables
user_states = {}
target_quiz = {}

# Store user information asynchronously
async def store_user_data(chat_id, username, first_name, last_name):
    # Create database and cursor object from the cursor class
    os.makedirs("db", exist_ok=True) # Create folder if it does not exist
    
    with sqlite3.connect("db/incolearn.db", timeout=20) as connection:
        cur = connection.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user(
                user_id INTEGER PRIMARY KEY, 
                username TEXT UNIQUE NOT NULL, 
                first_name TEXT NOT NULL, 
                last_name TEXT NOT NULL    
            )"""
        )
        # Commit the query and close the connection
        connection.commit()
        cur.close()
    
    print("Database user created successfully!") # For debugging purposes
    
    # Insert encrypted values if it does not exist yet
    try:
        with sqlite3.connect("db/incolearn.db", timeout=20) as connection:
            cur = connection.cursor()
            cur.execute("INSERT INTO user (user_id, username, first_name, last_name) VALUES(?, ?, ?, ?)", (chat_id, username, first_name, last_name))
            # Commit the query and close the connection
            connection.commit()
            cur.close()
        print("User inserted successfully!") # For debugging
 
    except sqlite3.IntegrityError:
        print("User already exists. Skipping insertion.")
    
async def create_quiz_table():
    try:
        # Create a table if there is none yet
        with sqlite3.connect("db/incolearn.db", timeout=20) as connection:
            cur = connection.cursor()
            cur.execute("""
                        CREATE TABLE IF NOT EXISTS quiz(
                            quiz_id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id INTEGER NOT NULL,
                            quiz_name TEXT UNIQUE NOT NULL,
                            FOREIGN KEY(user_id) REFERENCES user(user_id))
                        """)
            connection.commit()
            cur.close()
        print("Database quiz created successfully!") # For debugging
    except sqlite3.OperationalError as error:
        # For debugging
        print("Database user hasn't been created yet! Error message: ", error) # For debugging
        pass
            
async def create_question_table():
    try:
        # Create a database if it does not exist yet
        with sqlite3.connect("db/incolearn.db", timeout=20) as connection:
            cur = connection.cursor()
            cur.execute("""
                        CREATE TABLE IF NOT EXISTS question(
                            question_id INTEGER PRIMARY KEY AUTOINCREMENT,
                            quiz_id INTEGER NOT NULL,
                            question_text TEXT NOT NULL,
                            FOREIGN KEY(quiz_id) REFERENCES quiz(quiz_id))
                        """)
            connection.commit()
            cur.close()
        print("Database question created successfully!") # For debugging
    except sqlite3.OperationalError as error:
        print("Database quiz hasn't been created yet! Error message: ", error) # For debugging
        pass

# Remove the surrounding special characters from a tuple item
async def format_tuple_item(tuple_item):
    # Convert to string
    converted_tuple = str(tuple_item)
    
    # Get indexes
    end_index = len(converted_tuple) - 3
    start_index = 2
    
    # Slice string
    sliced_quiz_name = converted_tuple[start_index:end_index]
    
    return sliced_quiz_name
    

# For debugging
async def display_tables():
    try:
        # Display user table
        with sqlite3.connect("db/incolearn.db", timeout=20) as connection:
            cur = connection.cursor()
            cur.execute("SELECT * FROM user")
            rows = cur.fetchall()
            for row in rows:
                print(row)
            cur.close()
        
        # Display quiz table
        with sqlite3.connect("db/incolearn.db", timeout=20) as connection:
            cur = connection.cursor()
            cur.execute("SELECT * FROM quiz")
            rows = cur.fetchall()
            for row in rows:
                print(row)
            cur.close()
        
        # Display question table
        with sqlite3.connect("db/incolearn.db", timeout=20) as connection:
            cur = connection.cursor()
            cur.execute("SELECT * FROM question")
            rows = cur.fetchall()
            for row in rows:
                print(row)
            cur.close()
            
    except sqlite3.OperationalError as error:
        print("Database table hasn't been created yet. Error message: ", error)
        pass
        
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
    
    # For debugging
    print(text)
    # For debugging 
    display_tables()

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
    
    elif text == "/viewquizzes":
        try:
            with sqlite3.connect("db/incolearn.db", timeout=20) as connection:
                cur = connection.cursor()
                cur.execute("SELECT quiz_name FROM quiz")
                quiz_names = cur.fetchall()
                
            if len(quiz_names) == 0:
                bot_reply = "There are no saved quizzes yet! Create one by using /newquiz <quiz name>."
                
            else:
                builder = io.StringIO()
                builder.write("Here are your saved quizzes:")
                for quiz_name in quiz_names:
                    builder.write("\n")
                    formatted_name = await format_tuple_item(quiz_name)
                    builder.write(formatted_name)
                bot_reply = builder.getvalue()
            cur.close()
        except sqlite3.OperationalError:
            bot_reply = "There are no saved quizzes yet! Create one by using /newquiz <quiz name>."
                
    elif text.startswith("/editquiz"):
        chat_id = data['message']['chat']['id']
        
        # Obtain quiz names from the user's message and store them in a list
        current_quiz_name = text.replace("/editquiz", "").strip()
        print("Current quiz name: ", current_quiz_name)
        
        # Check if string is not empty
        if current_quiz_name:
            # Check if quiz exists  
            with sqlite3.connect("db/incolearn.db", timeout=20) as connection:
                cur = connection.cursor()
                cur.execute("SELECT * FROM quiz WHERE quiz_name=?", (current_quiz_name,))
                quiz = cur.fetchall()
                cur.close()
                
            # Reply when there is no quiz name given
            if len(quiz) == 0:
                bot_reply = "Quiz does not exist!"
                print("Quiz does not exist.") # For debugging
                
            else:
                bot_reply = "Please enter the new quiz name within 5 minutes."
                
                # Set user state and update target_quiz
                user_states[chat_id] = "awaiting_quiz_name"
                target_quiz[chat_id] = current_quiz_name
        else:
            bot_reply = "Invalid input. Make sure to follow this format /editquiz <quiz name>."
            print("User did not input the quiz name.") # For debugging
        
    elif text.startswith("/deletequiz"):
        chat_id = data['message']['chat']['id']
        
        # Obtain quiz names from the user's message and store them in a list
        quiz_name = text.replace("/deletequiz", "").strip()
        
        try:
            with sqlite3.connect("db/incolearn.db", timeout=20) as connection:
                cur = connection.cursor()
                cur.execute("DELETE FROM quiz WHERE quiz_name=? AND user_id=?", (quiz_name, chat_id))
                connection.commit()
                cur.close()
                
            bot_reply = f"Quiz {quiz_name} deleted."
        except UnboundLocalError as error:
            bot_reply = "Quiz does not exist. To create a new quiz, use /newquiz <quiz name>."
            print(error)
        except sqlite3.OperationalError as error:
            bot_reply = "Quiz does not exist. To create a new quiz, use /newquiz <quiz name>."
            print(error)
        
    elif user_states.get(chat_id) == "awaiting_question":        
        # Receive the message form the user and store it
        try:
            chat_id = data['message']['chat']['id']
            text = data['message']['text'].strip()
        except KeyError:
            return{"ok": False, "error": "No valid message"}
        
        # Store quiz name and question
        print(target_quiz[chat_id]) # For debugging
        question = text
        
        # Reset user state
        del user_states[chat_id]

        if text.strip():
            await create_question_table()
            
            # Retrieve quiz_id
            try:
                with sqlite3.connect("db/incolearn.db", timeout=20) as connection:
                    cur = connection.cursor()
                    cur.execute("SELECT * FROM quiz WHERE quiz_name=?", [target_quiz[chat_id]])
                    quiz = cur.fetchone()
                    quiz_id = quiz[0]
                    cur.close()
                    print("Quiz id retrieved!")

            except sqlite3.OperationalError as e:
                print("Database quiz hasn't been created yet!") # For debugging
                bot_reply="Quiz does not exist. Try checking your spelling or use /newquiz to create one."
                print("Error message: ", e)

            except TypeError as e:
                bot_reply="Quiz does not exist. Try checking your spelling or use /newquiz to create one."
                print("Error message: ", e)
                
            except UnboundLocalError as e:
                bot_reply="Quiz does not exist. Try checking your spelling or use /newquiz to create one."
                print("Error message: ", e)
                print("Database quiz hasn't been created yet!") # For debugging
                await create_quiz_table()
            
            try:
                # Insert question to the table
                with sqlite3.connect("db/incolearn.db", timeout=20) as connection:
                    cur = connection.cursor()
                    print(question) # For debugging
                    cur.execute("INSERT OR IGNORE INTO question (quiz_id, question_text) VALUES(?,?)", (quiz_id, question.replace("/addquestion","").strip()))
                    connection.commit()
                    cur.close()
                
                bot_reply = f"Question added to {target_quiz[chat_id]}!"
                del target_quiz[chat_id]
                    
                # For debugging
                print(question)
                await display_tables()   
                
            except UnboundLocalError as e: 
                bot_reply="Quiz does not exist. Try checking your spelling or use /newquiz to create one."
                print("Database quiz hasn't been created yet!") # For debugging
                print("Error: ", e)
                await create_quiz_table()
        else:
            bot_reply = "Question cannot be blank. Please try again and enter a valid question. Please try again with /addquestion <quiz name> then send the message afterwards."
            print("User took too long to respond.")
            
    elif user_states.get(chat_id) == "awaiting_quiz_name":        
        # Receive the message form the user and store it
        try:
            chat_id = data['message']['chat']['id']
            text = data['message']['text'].strip()
        except KeyError:
            return{"ok": False, "error": "No valid message"}
        
        # Store quiz name and question
        print(f"Current quiz name: {target_quiz[chat_id]}; New quiz name: {text.strip()}") # For debugging
        current_quiz_name = target_quiz[chat_id]
        new_quiz_name = text.strip()
        
        # Reset user state and target quiz
        del user_states[chat_id]
        del target_quiz[chat_id]

        if new_quiz_name:
            try:
                # Update quiz name if a user provides a valid one
                with sqlite3.connect("db/incolearn.db", timeout=20) as connection:
                    cur = connection.cursor()
                    print(question) # For debugging
                    cur.execute("UPDATE quiz SET quiz_name=? WHERE quiz_name=?", (new_quiz_name, current_quiz_name))
                    connection.commit()
                    cur.close()
                
                bot_reply = f"Quiz {current_quiz_name} was updated to {new_quiz_name}. Use /viewquizzes to view available quizzes."
                    
                # For debugging
                print(new_quiz_name)
                await display_tables()   
                
            except UnboundLocalError as e: 
                bot_reply="Quiz does not exist. Try checking your spelling or use /newquiz to create one."
                print("Database quiz hasn't been created yet!") # For debugging
                print("Error: ", e)
                await create_quiz_table()
        else:
            bot_reply = "Quiz name cannot be blank. Please try again and enter a valid quiz name."
            print("User took too long to respond.")
            
    elif user_states.get(chat_id) == "awaiting_quiz_name":        
        # Receive the message form the user and store it
        try:
            chat_id = data['message']['chat']['id']
            text = data['message']['text'].strip()
        except KeyError:
            return{"ok": False, "error": "No valid message"}
        
        # Store quiz name and question
        print(target_quiz[chat_id]) # For debugging
        question = text
        
        # Reset user state
        del user_states[chat_id]

        if text.strip():
            await create_question_table()
            
            # Retrieve quiz_id
            try:
                with sqlite3.connect("db/incolearn.db", timeout=20) as connection:
                    cur = connection.cursor()
                    cur.execute("SELECT * FROM quiz WHERE quiz_name=?", [target_quiz[chat_id]])
                    quiz = cur.fetchone()
                    quiz_id = quiz[0]
                    cur.close()
                    print("Quiz id retrieved!")

            except sqlite3.OperationalError as e:
                print("Database quiz hasn't been created yet!") # For debugging
                bot_reply="Quiz does not exist. Try checking your spelling or use /newquiz to create one."
                print("Error message: ", e)

            except TypeError as e:
                bot_reply="Quiz does not exist. Try checking your spelling or use /newquiz to create one."
                print("Error message: ", e)
                
            except UnboundLocalError as e:
                bot_reply="Quiz does not exist. Try checking your spelling or use /newquiz to create one."
                print("Error message: ", e)
                print("Database quiz hasn't been created yet!") # For debugging
                await create_quiz_table()
            
            try:
                # Insert question to the table
                with sqlite3.connect("db/incolearn.db", timeout=20) as connection:
                    cur = connection.cursor()
                    print(question) # For debugging
                    cur.execute("INSERT OR IGNORE INTO question (quiz_id, question_text) VALUES(?,?)", (quiz_id, question.replace("/addquestion","").strip()))
                    connection.commit()
                    cur.close()
                
                bot_reply = f"Question added to {target_quiz[chat_id]}!"
                del target_quiz[chat_id]
                    
                # For debugging
                print(question)
                await display_tables()   
                
            except UnboundLocalError as e: 
                bot_reply="Quiz does not exist. Try checking your spelling or use /newquiz to create one."
                print("Database quiz hasn't been created yet!") # For debugging
                print("Error: ", e)
                await create_quiz_table()
        else:
            bot_reply = "Question cannot be blank. Please try again and enter a valid question. Please try again with /addquestion <quiz name> then send the message afterwards."
            print("User took too long to respond.")
        
    elif text.startswith("/newquiz"):
        # Obtain user information
        from_user = data["message"]["from"]
        chat_id = data['message']['chat']['id']
        
        # Create a table if there is none yet
        await create_quiz_table()
        
        quiz_name = text.replace("/newquiz","").strip()
        print("Quiz name: ", quiz_name) # For debugging

        # Insert new quiz to the table
        try:
            with sqlite3.connect("db/incolearn.db", timeout=20) as connection:
                cur = connection.cursor()
                cur.execute("INSERT INTO quiz (quiz_name, user_id) VALUES(?,?)", (quiz_name, chat_id))
                connection.commit()
                cur.close()

            bot_reply = f"Quiz successfully created! To add questions to your newly created quiz, use the /addquestion {quiz_name} command."
        except:
            bot_reply = f"Quiz {quiz_name} already exist! Choose a different name or use /addquestion <quiz name> to add a question to the existing quiz."
        
        #For debugging
        await display_tables()
        
    elif text.startswith("/addquestion"):
        # Store quiz name
        quiz_name = text.replace("/addquestion", "").strip()
        print(quiz_name) # For debugging
        
        try:
            # Check if string is not empty
            if quiz_name.strip():
                # Check if quiz exists  
                with sqlite3.connect("db/incolearn.db", timeout=20) as connection:
                    cur = connection.cursor()
                    cur.execute("SELECT * FROM quiz WHERE quiz_name=?", (quiz_name,))
                    quiz = cur.fetchall()
                    cur.close()
            
                if len(quiz) == 0:
                    bot_reply = "Quiz does not exist!"
                else:
                    bot_reply = "Please enter the question within 5 minutes."
                    # Set user state
                    chat_id = data['message']['chat']['id']
                    user_states[chat_id] = "awaiting_question"
                    
                    # Update target quiz for user    
                    target_quiz[chat_id] = quiz_name
                
            else:
                bot_reply = "Quiz name cannot be empty. Try again using /addquestion <quiz name>."
                
        except sqlite3.OperationalError as error:
            print(error)
            bot_reply = "Quiz does not exist. Try checking your spelling or use /newquiz to create one."
            
    elif text == "/start":
        # Obtain user data then store it using a function
        from_user = data["message"]["from"]
        chat_id = data['message']['chat']['id']
        username = from_user.get("username") or "Not set"
        first_name = from_user.get("first_name") or "Not provided"
        last_name = from_user.get("last_name") or "Not provided"
        print(chat_id, username, first_name, last_name) # For debugging
        await store_user_data(chat_id, username, first_name, last_name)
        
        bot_reply = """
        Welcome to IncoLearn! To start creating your first quiz, type /newquiz. Type /help to view other available commands.
        """
        
    elif text.startswith("/feedback"):
        from_user = data["message"]["from"]
        username = from_user.get("username") or "Not set"
        
        # Send an e-mail
        s = smtplib.SMTP('smtp.gmail.com', 587)
        s.starttls()
        s.login("allenjames.laxamana03@gmail.com", "wercpudbvmtjhewo")
        message = f"IncoLearn user feedback from username: {username}\n\n{text.replace('/feedback', '').strip()}"
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

