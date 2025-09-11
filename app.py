import httpx
from fastapi import FastAPI, Request
from telebot.credentials import bot_token, bot_user_name, URL
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import os
import smtplib
import io
import datetime

TOKEN = bot_token
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

client = httpx.AsyncClient()

app = FastAPI()    

# Global variables
user_states = {}
target = {}
global_counter = {}
quiz_questions = {}
session_score = {}

# Send bot reply
async def reply(chat_id, message):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/sendMessage",
                json={"chat_id": chat_id, "text": message}
            )
            return response.json()
    except Exception as error:
        print(f"Error sending message: {error}")
        return None

# Get id 
async def fetch_id(column_name, table_name, row_name, row_value):
    try:
        with sqlite3.connect("db/incolearn.db", timeout=20) as connection:
            cur = connection.cursor()
            query = f"SELECT {column_name} FROM {table_name} WHERE {row_name} = ?"
            cur.execute(query, (row_value,))
            retrieved_value = cur.fetchone()
            cur.close()
            if retrieved_value:
                print("Retrieved value:", retrieved_value[0])
                return retrieved_value[0]
            else:
                print("No value found!")
                return None
            
    except Exception as error:
        print("Error in fetch_id function: ", error)
    
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
                            FOREIGN KEY(user_id) REFERENCES user(user_id) ON DELETE CASCADE
                            )
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
                            FOREIGN KEY(quiz_id) REFERENCES quiz(quiz_id) ON DELETE CASCADE
                        )
                        """)
            connection.commit()
            cur.close()
        print("Database question created successfully!") # For debugging
    except sqlite3.OperationalError as error:
        print("Database quiz hasn't been created yet! Error message: ", error) # For debugging
        pass
    
async def create_answer_table():
    try:
        with sqlite3.connect("db/incolearn.db", timeout=20) as connection:
            cur = connection.cursor()
            cur.execute("""
                        CREATE TABLE IF NOT EXISTS answer(
                            answer_id INTEGER PRIMARY KEY AUTOINCREMENT,
                            question_id INTEGER NOT NULL,
                            answer_text TEXT NOT NULL, 
                            FOREIGN KEY(question_id) REFERENCES question(question_id) ON DELETE CASCADE
                        )
                        """)
            connection.commit()
            cur.close()
        print("Database answer created successfully!") # For debugging
    except sqlite3.OperationalError as error:
        print("Database question hasn't been created yet! Error message: ", error) # For debugging
        pass    

async def create_attempt_table():
    try:
        with sqlite3.connect("db/incolearn.db", timeout=20) as connection:
            cur = connection.cursor()
            cur.execute("""
                        CREATE TABLE IF NOT EXISTS attempt(
                            attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
                            question_id INTEGER NOT NULL,
                            user_id INTEGER NOT NULL,
                            score INTEGER NOT NULL, 
                            attempt_date TEXT NOT NULL,
                            FOREIGN KEY(question_id) REFERENCES question(question_id) ON DELETE CASCADE,
                            FOREIGN KEY(user_id) REFERENCES user(user_id) ON DELETE CASCADE
                        )
                        """)
    except sqlite3.OperationalError as error:
        print("Database answer hasn't been created yet! Error message: ", error) # For debugging
        pass    
    
async def record_attempt(score, user_id, retrieved_question_id):
    await create_attempt_table() 
    with sqlite3.connect("db/incolearn.db", timeout=20) as connection:
        cur = connection.cursor()
        attempt_date = datetime.datetime.now()
        formatted_date = attempt_date.strftime("%x")
        cur.execute("INSERT INTO attempt (question_id, user_id, score, attempt_date) VALUES(?, ?, ?, ?)", (retrieved_question_id, user_id, score, formatted_date))
        cur.close()
    
# Check if the answer is correct then record attempt
async def check_answer(user_id, question, answer, chat_id): 
    # Format the answer
    answer = answer.strip().lower()
    
    # Fetch question id
    retrieved_question_id = await fetch_id("question_id", "question", "question_text", question)
    print("Question id: ", retrieved_question_id) # For debugging
    
    try:
        # Find matches in the answer table then compare the question ids
        if retrieved_question_id:
            with sqlite3.connect("db/incolearn.db", timeout=20) as connection:
                cur = connection.cursor()
                print("Answer: ", answer) # For debugging
                cur.execute("SELECT answer_text FROM answer WHERE question_id = ?", (retrieved_question_id,))
                retrieved_tuple = cur.fetchone()
                answer_from_table = retrieved_tuple[0]
                print("Retrieved answer: ", answer_from_table) # For debugging
                cur.close()
                
                if (answer == answer_from_table.strip().lower()):   
                    await record_attempt("1", user_id, retrieved_question_id)
                    print("Answers matched!")
                    bot_reply = "You got it right! A point is added to your total score."
                    session_score[chat_id] += 1 # Add one point to session score
                    await reply(chat_id, bot_reply)
                    return 
                
                else:
                    await record_attempt("0", user_id, retrieved_question_id)
                    print("Answers did not match.")
                    
                    with sqlite3.connect("db/incolearn.db", timeout=20) as connection:
                        cur = connection.cursor()
                        cur.execute("SELECT answer_text FROM answer WHERE question_id = ?", (retrieved_question_id,))
                        fetched_answer = cur.fetchone()
                        correct_answer = fetched_answer[0]
                        print("Correct answer: ", correct_answer) # For debugging
                        cur.close()
                        bot_reply = f"Incorrect. The correct answer is {correct_answer}."
                        await reply(chat_id, bot_reply)
                        return
        
        else:
            print("retrived_question_id not found.")
            bot_reply = "No answer has been added to that question yet. Please re-create the question using the /addquestion command."
            await reply(chat_id, bot_reply)
            return 
        
    except sqlite3.OperationalError as error:
        print("Error in check answer function: ", error)
        bot_reply = "There was an internal database error. Please contact the developer using /feedback."
        await reply(chat_id, bot_reply)
        return 
        
    except TypeError as error:
        try:
            await record_attempt("0", user_id, retrieved_question_id)
            print("Type error occured: ", error)
                        
            with sqlite3.connect("db/incolearn.db", timeout=20) as connection:
                            cur = connection.cursor()
                            cur.execute("SELECT answer_text FROM answer WHERE question_id = ?", (retrieved_question_id,))
                            fetched_answer = cur.fetchone()
                            correct_answer = fetched_answer[0]
                            print("Correct answer: ", correct_answer) # For debugging
                            cur.close()
                            bot_reply = f"Incorrect. The correct answer is {correct_answer}."
                            return bot_reply
        except Exception as error:
            print("Exception occured in the last except statement of check_answer:", error)
            bot_reply = "No answer has been added to that question yet. Please re-create the quiz using /addquestion <quiz name>."
            return
        await reply(chat_id, bot_reply)
    
async def handle_question(chat_id, answer):
    current_index = global_counter[chat_id] - 1
    await check_answer(chat_id, quiz_questions[chat_id][current_index], answer, chat_id)
    return   
    
# Function for /startquiz
async def show_question(chat_id):
        if global_counter.get(chat_id) == 0:
            print("EOF")
            del user_states[chat_id], global_counter[chat_id], target[chat_id], quiz_questions[chat_id] # Reset global variables
            return "Reached the end of the line."
        
        current_index = global_counter[chat_id] - 1
        current_question = quiz_questions[chat_id][current_index]
        await reply(chat_id, current_question) # Send question

        global_counter[chat_id] -= 1
        print("show_question passed")
        return 

# Remove the surrounding special characters from a tuple item
async def format_tuple_item(tuple_item):
    # Convert to string
    converted_tuple = str(tuple_item)
    
    # Get indexes
    end_index = len(converted_tuple) - 3
    start_index = 2
    
    # Slice string
    sliced_tuple = converted_tuple[start_index:end_index]
    
    return sliced_tuple
    

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
            
        # Display answer table
        with sqlite3.connect("db/incolearn.db", timeout=20) as connection:
            cur = connection.cursor()
            cur.execute("SELECT * FROM answer")
            rows = cur.fetchall()
            for row in rows:
                print(row)
            cur.close()
        
        # Display attempt table
        with sqlite3.connect("db/incolearn.db", timeout=20) as connection:
            cur = connection.cursor()
            cur.execute("SELECT * FROM attempt")
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
    await display_tables()

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
        /editquiz <quiz name> - Rename an existing quiz.
        /deletequiz <quiz name> - Delete a quiz. This cannot be undone.
        /randomquestion - Instantly get a random question from any of the existing quiz.
        /viewscore - Shows the user's total points.
        /feedback <message> - Send feedback about the bot to the developer.
        """
        await reply(chat_id, bot_reply)
    
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
        
        await reply(chat_id, bot_reply)
                
    elif text == "/viewscore":
        chat_id = data['message']['chat']['id']
        try:
            with sqlite3.connect("db/incolearn.db", timeout=20) as connection:
                cur = connection.cursor()
                cur.execute("SELECT COUNT(*) FROM attempt WHERE user_id=? AND score=1", (chat_id,))
                correct_attempts = cur.fetchone()[0]
                cur.close()
                bot_reply = f"In total, you accumulated {correct_attempts} points! Keep going nigga!"
        except Exception as error:
            print("Error in /viewscore block: ", error)
            bot_reply = "You haven't answered any question yet. To start answering, use /startquiz <quiz name> or /randomquestion."
        
        
    elif text.startswith("/startquiz"):
        chat_id = data['message']['chat']['id']
        text = text[10:].strip() # Slice and strip the quiz name
        print("Quiz name: ", text) # For debugging
        
        # Check if the quiz exists then store its id
        retrieved_quiz_id = await fetch_id("quiz_id", "quiz", "quiz_name", text)
        
        if retrieved_quiz_id:
            print("Retrieved quiz id: ", retrieved_quiz_id)
            user_states[chat_id] = "in_quiz"
            target[chat_id] = retrieved_quiz_id
            global_counter[chat_id] = None
            session_score[chat_id] = 0 # Initialize global variable
            bot_reply = "Please reply with your answer for each question."
            await reply(chat_id, bot_reply)

            if global_counter.get(chat_id) is None:
                # For debugging
                print("Current user state: ", user_states.get(chat_id))
                print("User id: ", chat_id)
                try:
                    with sqlite3.connect("db/incolearn.db", timeout=20) as connection:
                        cur = connection.cursor()
                        print("Target quiz id: ", target[chat_id]) # For debugging
                        target_quiz = target[chat_id]
                        cur.execute("SELECT question_text FROM question WHERE quiz_id = ?", (target_quiz,))
                        retrieved_rows = cur.fetchall()
                        set_of_questions = [row[0] for row in retrieved_rows]
                        global_counter[chat_id] = len(set_of_questions)
                        quiz_questions[chat_id] = set_of_questions
                        print("Number of questions: ", global_counter[chat_id]) # For debugging
                        for question in set_of_questions:
                            print(question) # For debugging
                        cur.close()
                        await show_question(chat_id)
                        
                except Exception as error:
                    print('Exception in "in_quiz" block: ', error)
                    bot_reply = "An error occured. Please contact the developer using /feedback."
                    await reply(chat_id, bot_reply)
                    return 
        else:
            bot_reply = "Quiz cannot be found! Please create the quiz first using /newquiz."
            await reply(chat_id, bot_reply)
        
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
                
                # Set user state and update target
                user_states[chat_id] = "awaiting_quiz_name"
                target[chat_id] = current_quiz_name
        else:
            bot_reply = "Invalid input. Make sure to follow this format /editquiz <quiz name>."
            print("User did not input the quiz name.") # For debugging
        
        await reply(chat_id, bot_reply)
        
    elif text.startswith("/deletequiz"):
        chat_id = data['message']['chat']['id']
        
        # Obtain quiz names from the user's message and store them in a list
        quiz_name = text.replace("/deletequiz", "").strip()
        
        try:
            with sqlite3.connect("db/incolearn.db", timeout=20) as connection:
                cur = connection.cursor()
                connection.execute("PRAGMA foreign_keys=ON")
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
        
        await reply(chat_id, bot_reply)
        
    elif user_states.get(chat_id) == "in_quiz":
        chat_id = data['message']['chat']['id']
        
        handle_question(chat_id, text)
        answer_check = await show_question(chat_id) # Call recursive function
        
        if answer_check == "Reached the end of the line.":
            bot_reply = f"Well done! You just finished the quiz! You scored a total of {session_score.get(chat_id)} points. Use /viewscore to see how much points were added."
            del session_score[chat_id]
            await reply(chat_id, bot_reply)
            
    elif user_states.get(chat_id) == "awaiting_question":        
        # Receive the message form the user and store it
        try:
            chat_id = data['message']['chat']['id']
            text = data['message']['text'].strip()
        except KeyError:
            return{"ok": False, "error": "No valid message"}
        
        # Store quiz name and question
        print(target[chat_id]) # For debugging
        question = text
        
        # Reset user state
        del user_states[chat_id]

        if text.strip():
            await create_question_table()
            
            # Retrieve quiz_id
            try:
                with sqlite3.connect("db/incolearn.db", timeout=20) as connection:
                    cur = connection.cursor()
                    cur.execute("SELECT * FROM quiz WHERE quiz_name=?", [target[chat_id]])
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
                
                bot_reply = f"Question added to {target[chat_id]}! Now, enter the answer to that question."
                del target[chat_id]
                    
                # For debugging
                print(question)
                await display_tables()   
                
                # Set global variables for answer input from user
                user_states[chat_id] = "awaiting_answer"
                target[chat_id] = await fetch_id("question_id", "question", "question_text", question)
                print("Current target: ", target[chat_id]) # For debugging
                
            except UnboundLocalError as e: 
                bot_reply="Quiz does not exist. Try checking your spelling or use /newquiz to create one."
                print("Database quiz hasn't been created yet!") # For debugging
                print("Error: ", e)
                await create_quiz_table()
        else:
            bot_reply = "Question cannot be blank. Please try again and enter a valid question. Please try again with /addquestion <quiz name> then send the message afterwards."
            print("User took too long to respond.")
        
        await reply(chat_id, bot_reply)
            
    elif user_states.get(chat_id) == "awaiting_quiz_name":        
        # Receive the message form the user and store it
        try:
            chat_id = data['message']['chat']['id']
            text = data['message']['text'].strip()
        except KeyError:
            return{"ok": False, "error": "No valid message"}
        
        # Store quiz name and question
        print(f"Current quiz name: {target[chat_id]}; New quiz name: {text.strip()}") # For debugging
        current_quiz_name = target[chat_id]
        new_quiz_name = text.strip()
        
        # Reset user state and target quiz
        del user_states[chat_id]
        del target[chat_id]

        if new_quiz_name:
            try:
                # Update quiz name if a user provides a valid one
                with sqlite3.connect("db/incolearn.db", timeout=20) as connection:
                    cur = connection.cursor()
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
            
        await reply(chat_id, bot_reply)
            
    elif user_states.get(chat_id) == "awaiting_answer":        
        # Receive the message form the user and store it
        try:
            chat_id = data['message']['chat']['id']
            text = data['message']['text'].strip()
        except KeyError:
            return{"ok": False, "error": "No valid message"}
        answer = text
        
        # Reset user state
        del user_states[chat_id]

        if answer:
            await create_answer_table()
            
            try:
                # Insert answer to the table
                with sqlite3.connect("db/incolearn.db", timeout=20) as connection:
                    cur = connection.cursor()
                    print(answer) # For debugging
                    question_id = target[chat_id]
                    cur.execute("INSERT OR IGNORE INTO answer (question_id, answer_text) VALUES(?,?)", (question_id, answer))
                    connection.commit()
                    cur.close()
                
                bot_reply = f"Answer added successfully!"
                del target[chat_id]
                    
                # For debugging
                print(answer)
                await display_tables()   
                
            except UnboundLocalError as e: 
                bot_reply="Quiz does not exist. Try checking your spelling or use /newquiz to create one."
                print("Database quiz hasn't been created yet!") # For debugging
                print("Error: ", e)
                await create_quiz_table()
        else:
            bot_reply = "Answer cannot be blank. Please try again and enter a valid question. Please try again."
            print("User took too long to respond.")
        
        await reply(chat_id, bot_reply)
        
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
        
        await reply(chat_id, bot_reply)
        
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
                    bot_reply = "Please enter the question."
                    # Set user state
                    chat_id = data['message']['chat']['id']
                    user_states[chat_id] = "awaiting_question"
                    
                    # Update target quiz for user    
                    target[chat_id] = quiz_name
                
            else:
                bot_reply = "Quiz name cannot be empty. Try again using /addquestion <quiz name>."
                
        except sqlite3.OperationalError as error:
            print(error)
            bot_reply = "Quiz does not exist. Try checking your spelling or use /newquiz to create one."
        
        await reply(chat_id, bot_reply)
        
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
        await reply(chat_id, bot_reply)
        
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
        
        bot_reply = "Feedback sent to the developer!"
        await reply(chat_id, bot_reply)
        
    elif text == "/randomquestion":    
        chat_id = data['message']['chat']['id']
        
        try:
            with sqlite3.connect("db/incolearn.db", timeout=20) as connection:
                cur = connection.cursor()
                cur.execute("SELECT question_text FROM question ORDER BY RANDOM() LIMIT 1")
                question = cur.fetchone()
                cur.close()
                
                # Set user states and target
                target[chat_id] = question
                session_score[chat_id] = 0
                user_states[chat_id] = "awaiting_random_answer"
                
                bot_reply = question[0]
        
        except sqlite3.OperationalError as error:
            print("Error in /randomquestion block: ", error)
            bot_reply = "No question has been added yet! Add a new one using /addquestion <quiz name>."
        
        await reply(chat_id, bot_reply)
                
    elif user_states.get(chat_id) == "awaiting_random_answer":
        # Store necessary parameters
        user_id = chat_id = data['message']['chat']['id']
        answer = text
        
        try: 
            # Check if the answer is correct using a function
            await check_answer(user_id, str(target[user_id][0]), answer, chat_id)
            del session_score[chat_id]
            pass
        except TypeError as error:
            print("Type error occured in awaiting_random_answer block: ", error)
            bot_reply = "No answer has been added to that question yet. Please re-create the quiz using /addquestion <quiz name>."
            await reply(chat_id, bot_reply)
        try:
            # Clear temporary variables
            del target[user_id], user_states[user_id], session_score[user_id]
        except KeyError as error:
            print("Key error encountered in awaiting_random_answer block: ", error)
            pass
        
    else:
        bot_reply = f"You said: {text}, which is not a valid command. Use /help to see the list of available commands."
        await reply(chat_id, bot_reply)
        
    return{"ok": True}

