# AlgoMentor: Socratic Algorithm Tutor Chatbot

AlgoMentor is a local AI tutoring app for algorithm problems. The student pastes a LeetCode or Codeforces-style problem, then the chatbot guides them step by step with hints instead of giving the final answer directly.

The project uses:

- Python
- Gradio for the web interface
- Ollama to run a local LLM
- Llama 3.2 3B as the local model
- ChromaDB for local vector storage
- Sentence Transformers for embeddings
- RAG to retrieve algorithm hints from a small knowledge base

---

## 1. What This Project Does

This project acts like a Socratic algorithm tutor.

Instead of saying:

> Use hashmap and here is the code.

It says things like:

> What kind of lookup would let you avoid reordering the array?

The goal is to help students think through the solution, not copy the answer.

---

## 2. Current Project Files

Your project currently has these main files:

```text
algo-tutor/
│
├── app.py
├── tutor.py
├── prompts.py
├── ingest.py
└── chroma_db/        generated after running ingest.py
```

### app.py

This file runs the Gradio web app.

It creates:

- problem input box
- Start Session button
- status box
- chatbot conversation area
- message box
- Send button

Run this file when you want to start the app.

### tutor.py

This is the main chatbot logic.

It handles:

- starting a new tutoring session
- classifying student messages
- detecting if the student is stuck
- detecting if the student asks for the answer
- storing confirmed ideas
- storing guesses
- retrieving relevant RAG chunks
- calling the local Ollama model
- checking if the LLM gave code or a direct answer
- replacing unsafe replies with safer hints

### prompts.py

This file stores the system prompt.

The system prompt tells the LLM to:

- behave like an algorithm tutor
- avoid giving code
- avoid giving the final answer
- ask one short guiding question
- keep responses short
- build on the student's previous ideas

### ingest.py

This file creates the local RAG database.

It stores algorithm tutoring knowledge in ChromaDB, including topics like:

- Dijkstra's algorithm
- dynamic programming
- BFS vs Dijkstra
- Two Sum

You must run this file before using the RAG part of the app.

---

## 3. How the App Works Internally

The flow is:

```text
Student opens Gradio app
        ↓
Student pastes problem
        ↓
app.py starts a new session
        ↓
Student sends a message
        ↓
tutor.py classifies the message
        ↓
RAG retrieves useful algorithm hints from ChromaDB
        ↓
prompts.py builds the tutor prompt
        ↓
Ollama runs llama3.2:3b locally
        ↓
tutor.py checks the response
        ↓
Safe hint is shown in the Gradio chatbot
```

The important part is that `tutor.py` does not blindly trust the LLM. It checks the response and blocks replies that look like direct solutions, code, or repeated hints.

---

## 4. Local Setup Guide

Follow these steps carefully.

---

## Step 1: Install Python

Install Python 3.10 or newer.

Check your version:

```bash
python --version
```

or:

```bash
py --version
```

If Python is installed correctly, you should see something like:

```text
Python 3.10.x
```

or newer.

---

## Step 2: Put All Files in One Folder

Create a folder, for example:

```text
C:\algo-tutor
```

Put these files inside that folder:

```text
app.py
tutor.py
prompts.py
ingest.py
```

Your folder should look like this:

```text
C:\algo-tutor\app.py
C:\algo-tutor\tutor.py
C:\algo-tutor\prompts.py
C:\algo-tutor\ingest.py
```

---

## Step 3: Open Terminal in the Project Folder

On Windows:

1. Open the folder where your files are saved.
2. Click the address bar.
3. Type:

```text
cmd
```

4. Press Enter.

Now your terminal should open inside the project folder.

You can check using:

```bash
dir
```

You should see:

```text
app.py
tutor.py
prompts.py
ingest.py
```

---

## Step 4: Create a Virtual Environment

Run:

```bash
python -m venv venv
```

If `python` does not work, try:

```bash
py -m venv venv
```

This creates a local environment named `venv`.

---

## Step 5: Activate the Virtual Environment

On Windows CMD:

```bash
venv\Scripts\activate
```

On PowerShell:

```bash
.\venv\Scripts\Activate.ps1
```

If PowerShell blocks it, use CMD instead.

After activation, your terminal should show something like:

```text
(venv) C:\algo-tutor>
```

---

## Step 6: Install Required Python Packages

Run:

```bash
pip install gradio ollama chromadb sentence-transformers
```

This may take a few minutes.

---

## Step 7: Install Ollama

Install Ollama from the official Ollama website.

After installing it, open a new terminal and check:

```bash
ollama --version
```

If it shows a version number, Ollama is installed.

---

## Step 8: Download the Local LLM Model

Run:

```bash
ollama pull llama3.2:3b
```

This downloads the model used in `tutor.py`.

The project currently has this line:

```python
MODEL = "llama3.2:3b"
```

So the model name must match exactly.

---

## Step 9: Make Sure Ollama Is Running

Usually Ollama runs automatically in the background.

To test it, run:

```bash
ollama run llama3.2:3b
```

Type a quick test message like:

```text
hello
```

If the model replies, Ollama is working.

To exit Ollama chat, type:

```text
/bye
```

---

## Step 10: Create the ChromaDB Knowledge Base

Now go back to your project folder terminal where the virtual environment is activated.

Run:

```bash
python ingest.py
```

Expected output:

```text
Ingested 7 chunks into ChromaDB.
```

This creates a folder called:

```text
chroma_db
```

That folder stores your local RAG knowledge base.

---

## Step 11: Run the App

Run:

```bash
python app.py
```

You should see something like:

```text
Running on local URL: http://127.0.0.1:7860
```

Open that link in your browser.

Because your current `app.py` has:

```python
demo.launch(share=True)
```

Gradio may also create a public share link. For local testing, the local link is enough.

If you only want local mode, change the last line in `app.py` from:

```python
demo.launch(share=True)
```

to:

```python
demo.launch()
```

---

## Step 12: Test With a Sample Problem

Paste this into the Problem box:

```text
Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target. You may assume that each input has exactly one solution, and you may not use the same element twice.
```

Click:

```text
Start Session
```

Then send this message:

```text
Can I use sorting?
```

Expected style of response:

```text
No, sorting changes the order, which makes the original indices harder to recover. What kind of lookup would let you avoid reordering the array?
```

Then try:

```text
Maybe hashmap?
```

Expected style of response:

```text
Yes, that direction makes sense because it gives fast lookup. What should the key and value represent?
```

---

## 5. Common Errors and Fixes

### Error: ModuleNotFoundError

Example:

```text
ModuleNotFoundError: No module named 'gradio'
```

Fix:

Make sure your virtual environment is activated, then run:

```bash
pip install gradio ollama chromadb sentence-transformers
```

---

### Error: Ollama connection error

If you see an error related to Ollama connection, make sure Ollama is installed and running.

Test with:

```bash
ollama run llama3.2:3b
```

---

### Error: Model not found

If the model is missing, run:

```bash
ollama pull llama3.2:3b
```

---

### Error: ChromaDB has no data

If the chatbot gives weak responses or RAG seems empty, run:

```bash
python ingest.py
```

Then run:

```bash
python app.py
```

again.

---

### Error: The browser does not open automatically

Copy the local URL from the terminal manually.

Example:

```text
http://127.0.0.1:7860
```

Paste it into Chrome or Edge.

---

## 6. Recommended requirements.txt

Create a file named:

```text
requirements.txt
```

Put this inside:

```text
gradio
ollama
chromadb
sentence-transformers
```

Then next time, you can install everything using:

```bash
pip install -r requirements.txt
```

---

## 7. Recommended Local Run Commands

For Windows CMD, the full run sequence is:

```bash
cd C:\algo-tutor
python -m venv venv
venv\Scripts\activate
pip install gradio ollama chromadb sentence-transformers
ollama pull llama3.2:3b
python ingest.py
python app.py
```

After that, open:

```text
http://127.0.0.1:7860
```

---

## 8. Important Notes

- The model runs locally through Ollama.
- The app interface runs through Gradio.
- The RAG database is stored locally in the `chroma_db` folder.
- Run `ingest.py` at least once before running the app.
- Keep `app.py`, `tutor.py`, `prompts.py`, and `ingest.py` in the same folder.
- Do not delete `chroma_db` unless you want to rebuild the knowledge base.
- If you edit the corpus inside `ingest.py`, run `python ingest.py` again.

---

## 9. Future Improvements

Possible improvements:

- Add more LeetCode problems to the corpus
- Add more algorithm topics
- Add a reset button
- Add difficulty levels for hints
- Store previous sessions
- Add code testing
- Add support for student-submitted code
- Improve UI design
- Add requirements.txt
- Add README screenshots

---

## 10. Final Summary

AlgoMentor is a local Socratic algorithm tutor. It uses a local LLM and a small RAG knowledge base to guide students through algorithm problems without directly giving the final answer. The main purpose is to help students learn how to think through algorithm problems step by step.
