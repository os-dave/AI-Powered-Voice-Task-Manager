import json
import re
import speech_recognition as sr
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnableSequence
from langchain_community.utilities import SQLDatabase
from langchain.output_parsers import StructuredOutputParser, ResponseSchema
from dotenv import load_dotenv
from dateutil import parser as date_parser
import os
import sqlite3

load_dotenv()

# Set up database
db = SQLDatabase.from_uri("sqlite:///project_planner.db")


def update_database_schema():
    conn = sqlite3.connect("project_planner.db")
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task TEXT NOT NULL,
        timeframe TEXT NOT NULL,
        details TEXT,
        due_date DATETIME
    )
    ''')
    conn.commit()
    conn.close()


update_database_schema()

# Set up LLM with API key and specific model
llm = ChatOpenAI(
    temperature=0,
    model_name="gpt-4o-mini",
    api_key=os.getenv('OPENAI')
)

# Set up output parser for JSON responses
response_schemas = [
    ResponseSchema(name="task", description="The task or goal described"),
    ResponseSchema(
        name="timeframe", description="The timeframe for the task (e.g., '5-year vision', 'today')"),
    ResponseSchema(
        name="details", description="Additional details about the task")
]
output_parser = StructuredOutputParser.from_response_schemas(response_schemas)

# Set up prompt template for task creation
create_template = """
You are an AI assistant for project planning. Based on the user's input, provide a response and structure it as follows:
{format_instructions}

User input: {user_input}
"""

create_prompt = PromptTemplate(
    template=create_template,
    input_variables=["user_input"],
    partial_variables={
        "format_instructions": output_parser.get_format_instructions()}
)

create_chain = RunnableSequence(
    create_prompt,
    llm,
    output_parser
)

# Set up prompt template for task retrieval
retrieve_template = """
You are an AI assistant for project planning. The user wants to retrieve tasks. 
Based on the user's input, generate an SQL query to retrieve the relevant tasks.
The tasks table has the following columns: id, task, timeframe, details, due_date.

Use the appropriate column names in your query. If the user's request involves dates,
use the due_date column in your query.

User input: {user_input}

SQL query:
"""

retrieve_prompt = PromptTemplate(
    template=retrieve_template,
    input_variables=["user_input"]
)

retrieve_chain = RunnableSequence(
    retrieve_prompt,
    llm
)


def clean_sql_query(query):
    # Remove markdown formatting
    query = re.sub(r'```sql|```', '', query)
    # Remove any leading/trailing whitespace
    return query.strip()


def parse_due_date(timeframe):
    try:
        return date_parser.parse(timeframe)
    except:
        return None


def speech_to_text():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Speak now:")
        audio = recognizer.listen(source)
    try:
        return recognizer.recognize_google(audio)
    except sr.UnknownValueError:
        print("Could not understand audio")
        return None


def save_task(task):
    conn = sqlite3.connect("project_planner.db")
    cursor = conn.cursor()
    due_date = parse_due_date(task['timeframe'])
    cursor.execute("INSERT INTO tasks (task, timeframe, details, due_date) VALUES (?, ?, ?, ?)",
                   (task['task'], task['timeframe'], task['details'], due_date))
    conn.commit()
    conn.close()


def retrieve_tasks(query):
    conn = sqlite3.connect("project_planner.db")
    cursor = conn.cursor()
    try:
        cursor.execute(query)
        tasks = cursor.fetchall()
        print(f"Retrieved {len(tasks)} tasks")  # Logging
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        tasks = []
    finally:
        conn.close()
    return tasks


def log_all_tasks():
    conn = sqlite3.connect("project_planner.db")
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM tasks")
        tasks = cursor.fetchall()
        print("All tasks in the database:")
        for task in tasks:
            print(
                f"ID: {task[0]}, Task: {task[1]}, Timeframe: {task[2]}, Details: {task[3]}, Due Date: {task[4]}")
    except sqlite3.Error as e:
        print(f"An error occurred while logging tasks: {e}")
    finally:
        conn.close()


# Main loop
while True:
    print("Say 'create task' to add a new task or 'retrieve tasks' to get existing tasks.")
    user_intent = speech_to_text()

    if user_intent is None:
        continue

    if "create task" in user_intent.lower():
        print("What task would you like to add?")
        user_input = speech_to_text()
        if user_input is None:
            continue

        response = create_chain.invoke({"user_input": user_input})
        print(json.dumps(response, indent=2))
        save_task(response)
        print("Task saved successfully!")

    elif "retrieve tasks" in user_intent.lower():
        print("What tasks would you like to retrieve?")
        user_input = speech_to_text()
        if user_input is None:
            continue

        ai_response = retrieve_chain.invoke({"user_input": user_input})
        if isinstance(ai_response, str):
            query = ai_response
        elif hasattr(ai_response, 'content'):
            query = ai_response.content
        else:
            print("Error: Unexpected response format from AI.")
            continue

        query = clean_sql_query(query)
        print(f"Generated SQL query: {query}")

        tasks = retrieve_tasks(query)
        if tasks:
            print("Retrieved tasks:")
            for task in tasks:
                print(
                    f"ID: {task[0]}, Task: {task[1]}, Timeframe: {task[2]}, Details: {task[3]}, Due Date: {task[4]}")
        else:
            print("No tasks found matching your criteria.")

    elif "exit" in user_intent.lower():
        break

    else:
        print("Sorry, I didn't understand. Please try again.")
