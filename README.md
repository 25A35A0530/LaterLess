
# LaterLess — Let Your Local AI Handle the Busywork

**LaterLess** is a local AI-powered file organizer that helps reduce the time spent organizing files manually. It uses an open-source AI model through Ollama to suggest meaningful file categories and cleaner filenames, allowing users to review and approve changes before applying them.

Built for the **Hacktoberfest Open-Source AI Challenge — Week 3: Slow and Steady**.

## ✨ Features

- **AI-powered suggestions:** Uses a locally running AI model to suggest file categories and cleaner filenames.
- **File scanning:** Scans files in the selected sample folder.
- **Preview before applying:** Lets users review suggestions before making changes.
- **Selective organization:** Allows users to choose which suggested changes to apply.
- **Automatic organization:** Moves approved files into category folders and renames them.
- **Undo support:** Provides an option to reverse the last organization operation.
- **Local AI processing:** Uses Ollama to run the AI model locally.
- **Simple web interface:** Provides an easy-to-use interface for scanning, reviewing, organizing, and restoring files.

## 🎯 Problem Statement

Manually organizing files can be repetitive and time-consuming. Files often accumulate in folders with unclear names and no consistent structure.

LaterLess aims to simplify this process by using local AI to recommend file categories and clearer filenames, while keeping users in control of the changes.

## 💡 How It Works

1. Start the LaterLess server.
2. Open the web interface in your browser.
3. Scan the sample files.
4. Ask the AI to suggest categories and filenames.
5. Review the suggestions and select the changes you want.
6. Apply the approved changes.
7. Use **Undo Last Operation** if you want to reverse the last organization operation.

## 🛠️ Tech Stack

- **Python** — Backend and file operations
- **HTML, CSS, JavaScript** — Frontend
- **Ollama** — Local AI model runtime
- **Qwen2.5-Coder 3B** — AI model used for suggestions

## 📁 Project Structure

```text
LaterLess/
├── server.py
├── index.html
├── README.md
└── sample_files/
    └── demo/
        ├── notes.txt
        ├── python_practice.py
        ├── expenses.csv
        └── project_slides.txt
```

*Note: Category folders and generated history files may appear after running the application.*

## ⚙️ Requirements

- Python 3.10 or a compatible version
- Ollama installed and running
- The `qwen2.5-coder:3b` model downloaded
- A modern web browser

## 🚀 Installation and Setup

### 1. Install Ollama

Download and install Ollama from:

https://ollama.com/

### 2. Download the AI model

Open Command Prompt and run:

```bash
ollama pull qwen2.5-coder:3b
```

Make sure Ollama is running before requesting AI suggestions.

### 3. Open the project directory

In Windows Command Prompt, run:

```cmd
cd /d "C:\Users\Spandana\OneDrive\Desktop\LaterLess"
```

### 4. Start the application

Run:

```cmd
python server.py
```

Wait for the server startup message.

### 5. Open LaterLess

Visit the following address in your browser:

http://127.0.0.1:8000

## 🧪 Testing the Application

Use the included sample files to test the workflow.

- [ ] Check that the server and Ollama model are available.
- [ ] Scan the sample files.
- [ ] Generate AI organization suggestions.
- [ ] Select one or more suggestions.
- [ ] Apply the approved changes.
- [ ] Verify that the files appear in the expected category folders.
- [ ] Undo the last organization operation.
- [ ] Verify that the files return to their original locations and names.

## 🔒 Privacy and Safety

LaterLess is designed to use a locally running AI model, reducing the need to send file contents to a hosted AI service for suggestions.

- Review suggested changes before applying them.
- Test with sample files before using important personal files.
- Keep backups of important data.
- Do not expose the local server to an untrusted network.
- Local AI usage does not automatically guarantee that every part of an application is private; review the backend and any external connections before relying on it for sensitive files.

## 🌱 Future Improvements

- Support selecting folders through the web interface.
- Improve file-type detection and category suggestions.
- Add batch organization and clearer operation history.
- Add safeguards for filename conflicts.
- Improve error messages and recovery options.
- Add automated tests for file operations and undo behavior.

## 📜 License

This project is intended as an open-source learning project. A license has not yet been selected. Add a `LICENSE` file before publishing if you want to specify the terms under which others may use, modify, and distribute the project.

## 👩‍💻 Author

**Spandana**

Built as part of the Hacktoberfest Open-Source AI Challenge — Week 3: *Slow and Steady*.
