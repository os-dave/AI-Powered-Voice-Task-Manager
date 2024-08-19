# AI-Powered Voice Task Manager

## Prerequisites

- Python 3.8+
- PyAudio

## Installation

1. Clone the repository:

   ```
   git clone https://github.com/os-dave/AI-Powered-Voice-Task-Manager.git
   cd AI-Powered-Voice-Task-Manager
   ```

2. Install dependencies:

   ```
   pip install -r requirements.txt
   ```

3. Install PyAudio:

   - On most systems:
     ```
     pip install pyaudio
     ```
   - On macOS, if the above fails:
     ```
     brew install portaudio
     pip install pyaudio
     ```

4. Set up your OpenAI API key:
   - Create a `.env` file in the project root
   - Add your API key: `OPENAI=your_api_key_here`

## Usage

1. Run the script:

   ```
   python main.py
   ```

2. Voice Commands:

   - Say "create task" to add a new task
   - Say "retrieve tasks" to fetch existing tasks
   - Say "exit" to end the program

3. Follow the prompts to input task details or retrieval criteria.

## Troubleshooting

- If you encounter a "No module named 'pyaudio'" error, follow the PyAudio installation steps in the Installation section.
- Ensure your microphone is properly connected and configured.
- Check the console output for any error messages or SQL queries for debugging.

## Contributing

1. Fork the repository
2. Create a new branch for your feature
3. Submit a pull request with a clear description of your changes

## License

This project is licensed under the MIT License - see the LICENSE file for details.
