# Project Chrono: AI-Powered Voice Task Manager

## Prerequisites

- Python 3.8+
- PyAudio

## Installation

1. Clone the repository:

   ```
   git clone https://github.com/yourusername/project-chrono.git
   cd project-chrono
   ```

2. Create and activate a virtual environment:

   ```
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows, use `.venv\Scripts\activate`
   ```

3. Install dependencies:

   ```
   pip install -r requirements.txt
   ```

4. Install PyAudio:

   - On most systems:
     ```
     pip install pyaudio
     ```
   - On macOS, if the above fails:
     ```
     brew install portaudio
     pip install pyaudio
     ```
   - If you're still having issues, download the appropriate wheel from [here](https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio) and install it:
     ```
     pip install path/to/PyAudio-0.2.11-cp311-cp311-win_amd64.whl
     ```
     (Replace the filename with the one you downloaded)

5. Set up your OpenAI API key:
   - Create a `.env` file in the project root
   - Add your API key: `OPENAI=your_api_key_here`

## Usage

1. Activate the virtual environment (if not already activated):

   ```
   source .venv/bin/activate  # On Windows, use `.venv\Scripts\activate`
   ```

2. Run the script:

   ```
   python main.py
   ```

3. Voice Commands:

   - Say "create task" to add a new task
   - Say "retrieve tasks" to fetch existing tasks
   - Say "exit" to end the program

4. Follow the prompts to input task details or retrieval criteria.

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
