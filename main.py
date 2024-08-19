import json
import re
from datetime import datetime, time
import speech_recognition as sr
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnableSequence
from langchain_core.messages import AIMessage
from langchain_community.utilities import SQLDatabase
from langchain.output_parsers import StructuredOutputParser, ResponseSchema
from dotenv import load_dotenv
from dateutil import parser as date_parser
import os
import sqlite3

load_dotenv()

# Set up database
db = SQLDatabase.from_uri("sqlite:///project_planner.db")


def parse_due_date_and_time(task):
    due_date = task.get('due_date')

    print(f"Parsing due date and time for task: {task['task']}")
    print(f"Due date from task: {due_date}")

    # Parse the due_date from the input
    parsed_date = datetime.strptime(due_date, "%Y-%m-%d").date()

    # Always use 12:00 PM as the time
    parsed_time = time(12, 0)

    # Combine the date from due_date and fixed time
    full_datetime = datetime.combine(parsed_date, parsed_time)
    print(f"Parsed datetime: {full_datetime}")
    return full_datetime


def save_task(task):
    conn = sqlite3.connect("project_planner.db")
    cursor = conn.cursor()

    due_date = parse_due_date_and_time(task)
    due_date_str = due_date.strftime(
        "%Y-%m-%d %H:%M:%S")  # Format including time

    cursor.execute("INSERT INTO tasks (task, timeframe, details, due_date) VALUES (?, ?, ?, ?)",
                   (task['task'], task['timeframe'], task['details'], due_date_str))
    conn.commit()

    # Debug: Print the inserted task
    cursor.execute("SELECT * FROM tasks WHERE id = last_insert_rowid()")
    inserted_task = cursor.fetchone()
    print("Inserted task:")
    print(inserted_task)

    conn.close()

    print("Task saved successfully!")
    print(f"Task: {task['task']}")
    print(f"Timeframe: {task['timeframe']}")
    print(f"Details: {task['details']}")
    print(f"Due Date saved: {due_date_str}")


def update_database_schema():
    conn = sqlite3.connect("project_planner.db")
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task TEXT NOT NULL,
        timeframe TEXT NOT NULL,
        details TEXT,
        due_date TEXT
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
        name="due_date", description="The specific due date for the task (in YYYY-MM-DD format)"),
    ResponseSchema(
        name="details", description="Additional details about the task")
]
output_parser = StructuredOutputParser.from_response_schemas(response_schemas)

# Set up prompt template for task creation
create_template = """
You are an AI assistant for project planning. Based on the user's input, provide a response and structure it as follows:
{format_instructions}

When possible, interpret the timeframe to provide a specific due date in YYYY-MM-DD format.
If no specific date can be determined, leave the due_date field empty.

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
You are an AI assistant for project planning. The user wants to retrieve tasks from the 'tasks' table.
Generate a SQL query based on the user's input. The table has these columns: id, task, timeframe, details, due_date.

The due_date is stored as a string in the format 'YYYY-MM-DD HH:MM:SS'.

ALWAYS use this format for your response, replacing CONDITION with appropriate SQL conditions:
SELECT * FROM tasks WHERE CONDITION;

If no specific condition is needed, use:
SELECT * FROM tasks;

User input: {user_input}

SQL query:
"""

retrieve_prompt = PromptTemplate(
    template=retrieve_template,
    input_variables=["user_input"]
)


def ensure_valid_query(message):
    if isinstance(message, AIMessage):
        query = message.content
    elif isinstance(message, str):
        query = message
    else:
        raise ValueError(f"Unexpected type for query: {type(message)}")

    if not query.strip().lower().startswith("select"):
        query = "SELECT * FROM tasks;"
    if not query.strip().endswith(";"):
        query = query.strip() + ";"
    return query


retrieve_chain = RunnableSequence(
    retrieve_prompt,
    llm
)


def clean_sql_query(query):
    # Remove any explanatory text before or after the actual SQL query
    sql_pattern = r'SELECT.*?FROM.*?(WHERE.*?)?;?'
    match = re.search(sql_pattern, query, re.IGNORECASE | re.DOTALL)
    if match:
        clean_query = match.group(0)
        # Ensure the query ends with a semicolon
        if not clean_query.strip().endswith(';'):
            clean_query += ';'
        return clean_query
    else:
        raise ValueError("No valid SQL query found in the generated text.")


def parse_due_date_and_time(task):
    due_date = task.get('due_date')
    details = task.get('details', '')

    print(f"Parsing due date and time for task: {task['task']}")
    print(f"Due date from task: {due_date}")
    print(f"Details: {details}")

    # Try to extract time from details
    time_match = re.search(
        r'(\d{1,2}:\d{2}\s*(?:a\.m\.|p\.m\.))', details, re.IGNORECASE)

    if time_match:
        print(f"Time found in details: {time_match.group(1)}")
    else:
        print("No time found in details")

    if due_date:
        try:
            parsed_date = date_parser.parse(due_date).date()
            if time_match:
                parsed_time = date_parser.parse(time_match.group(1)).time()
            else:
                # Default to midnight if no time specified
                parsed_time = time(0, 0)

            full_datetime = datetime.combine(parsed_date, parsed_time)
            print(f"Parsed datetime: {full_datetime}")
            return full_datetime
        except ValueError as e:
            print(f"Failed to parse date/time: {e}")

    print("Returning None as due date")
    return None


def speech_to_text():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Speak now:")
        audio = recognizer.listen(source)
    try:
        return recognizer.recognize_google(audio)
    except sr.UnknownValueError:
        print("Sorry, I didn't understand. Please try again.")
        return None


def save_task(task):
    conn = sqlite3.connect("project_planner.db")
    cursor = conn.cursor()

    due_date = parse_due_date_and_time(task)
    due_date_str = due_date.strftime(
        "%Y-%m-%d %H:%M:%S")  # Format including time

    cursor.execute("INSERT INTO tasks (task, timeframe, details, due_date) VALUES (?, ?, ?, ?)",
                   (task['task'], task['timeframe'], task['details'], due_date_str))
    conn.commit()

    # Debug: Print the inserted task
    cursor.execute("SELECT * FROM tasks WHERE id = last_insert_rowid()")
    inserted_task = cursor.fetchone()
    print("Inserted task:")
    print(inserted_task)

    conn.close()

    print("Task saved successfully!")
    print(f"Task: {task['task']}")
    print(f"Timeframe: {task['timeframe']}")
    print(f"Details: {task['details']}")
    print(f"Due Date saved: {due_date_str}")


def retrieve_tasks(query):
    conn = sqlite3.connect("project_planner.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute(query)
        tasks = cursor.fetchall()
        print(f"Retrieved {len(tasks)} tasks")
        return [dict(task) for task in tasks]
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        return []
    finally:
        conn.close()


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


def main():
    while True:
        print("\n=== Task Manager ===")
        print(
            "Say 'create task' to add a new task or 'retrieve tasks' to get existing tasks.")
        print("Say 'exit' to quit the program.")
        user_intent = speech_to_text()

        if user_intent is None:
            continue

        if "create task" in user_intent.lower():
            print("\n--- Create New Task ---")
            print("Please describe the task you'd like to add:")
            user_input = speech_to_text()
            if user_input is None:
                continue

            response = create_chain.invoke({"user_input": user_input})
            save_task(response)

        elif "retrieve tasks" in user_intent.lower():
            print("\n--- Retrieve Tasks ---")
            print("What tasks would you like to retrieve?")
            user_input = speech_to_text()
            if user_input is None:
                continue

            ai_response = retrieve_chain.invoke({"user_input": user_input})
            query = ensure_valid_query(ai_response)
            print(f"Executing query: {query}")

            try:
                tasks = retrieve_tasks(query)
                if tasks:
                    print("\nRetrieved tasks:")
                    for task in tasks:
                        due_date = task['due_date']
                        print(f"ID: {task['id']}, Task: {task['task']}, Timeframe: {task['timeframe']}, "
                              f"Details: {task['details']}, Due Date: {due_date}")
                else:
                    print("No tasks found matching your criteria.")
            except sqlite3.Error as e:
                print(f"Database error: {e}")

        elif "exit" in user_intent.lower():
            print("Thank you for using Task Manager. Goodbye!")
            break

        else:
            print("Sorry, I didn't understand. Please try again.")


if __name__ == "__main__":
    main()
