import re
from datetime import datetime, time
import speech_recognition as sr
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnableSequence
from langchain.output_parsers import StructuredOutputParser, ResponseSchema
from dotenv import load_dotenv
from dateutil import parser as date_parser
import os
from langchain.schema import AIMessage
import sqlite3

load_dotenv()


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


llm = ChatOpenAI(
    temperature=0,
    model_name="gpt-4o-mini",
    api_key=os.getenv('OPENAI')
)

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


def ensure_valid_query(query):
    if isinstance(query, AIMessage):
        query_text = query.content
    elif isinstance(query, str):
        query_text = query
    else:
        raise ValueError(f"Unexpected query type: {type(query)}")

    if not query_text.strip().lower().startswith("select"):
        query_text = "SELECT * FROM tasks;"
    if not query_text.strip().endswith(";"):
        query_text = query_text.strip() + ";"
    return query_text


retrieve_chain = RunnableSequence(
    retrieve_prompt,
    llm
)


def parse_due_date_and_time(task):
    due_date = task.get('due_date')
    details = task.get('details', '')

    time_match = re.search(
        r'(\d{1,2}:\d{2}\s*(?:a\.m\.|p\.m\.))', details, re.IGNORECASE)

    if due_date:
        try:
            parsed_date = date_parser.parse(due_date).date()
            parsed_time = date_parser.parse(time_match.group(
                1)).time() if time_match else time(0, 0)
            return datetime.combine(parsed_date, parsed_time)
        except ValueError:
            pass
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
    due_date_str = due_date.strftime("%Y-%m-%d %H:%M:%S") if due_date else None

    cursor.execute("INSERT INTO tasks (task, timeframe, details, due_date) VALUES (?, ?, ?, ?)",
                   (task['task'], task['timeframe'], task['details'], due_date_str))
    conn.commit()
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


def main():
    while True:
        print("\n=== Task Manager ===")
        print(
            "Say 'create task' to add a new task or 'retrieve tasks' to get existing tasks.")
        print("Say 'exit' to quit the program.")
        user_intent = speech_to_text()

        if user_intent is None:
            continue

        print(f"You said: {user_intent}")

        if "create task" in user_intent.lower():
            print("\n--- Create New Task ---")
            print("Please describe the task you'd like to add:")
            user_input = speech_to_text()
            if user_input is None:
                continue

            print(f"You said: {user_input}")

            response = create_chain.invoke({"user_input": user_input})
            save_task(response)

        elif "retrieve tasks" in user_intent.lower():
            print("\n--- Retrieve Tasks ---")
            print("What tasks would you like to retrieve?")
            user_input = speech_to_text()
            if user_input is None:
                continue

            print(f"You said: {user_input}")

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
    update_database_schema()
    main()
