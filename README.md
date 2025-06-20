# Document Q&A Chat Application 🤖📚

A smart chat application that reads your PDF documents and answers questions about them! Just upload your PDFs, ask questions in natural language, and get intelligent answers based on your document content.

## What Does This Do? 🤔

Imagine having a smart assistant that has read all your PDF documents and can instantly answer any question about them. That's exactly what this application does!

- **Upload PDFs**: Place your PDF files in the project folder
- **Ask Questions**: Type questions like "What are the key findings?" or "Summarize the main points"
- **Get Smart Answers**: The AI reads through your documents and gives you accurate, relevant answers
- **Chat Interface**: Have a natural conversation about your documents

## Before You Start 📋

You'll need these installed on your computer:

### 1. Python (3.13 or newer)
**Check if you have Python:**
```bash
python --version
```

**If you don't have Python 3.13+:**
- **Windows/Mac**: Download from [python.org](https://www.python.org/downloads/)
- **Mac with Homebrew**: `brew install python@3.13`
- **Ubuntu/Debian**: `sudo apt update && sudo apt install python3.13`

### 2. Docker (for the database)
**Check if you have Docker:**
```bash
docker --version
```

**If you don't have Docker:**
- **Windows/Mac**: Download [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- **Ubuntu**: Follow [Docker's official guide](https://docs.docker.com/engine/install/ubuntu/)

### 3. uv (Python package manager)
**Install uv:**
```bash
# On Windows/Mac/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# On Windows with PowerShell
powershell -c "irm https://astral.sh/uv/install.sh | iex"

# Restart your terminal after installation
```

### 4. Google Gemini API Key (Free!)
1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the key (you'll need it later)

## Step-by-Step Setup 🚀

### Step 1: Download This Project

   ```bash
# Download the project (replace with your actual download method)
# If you have git:
git clone <your-repository-url>
cd dor

# Or download as ZIP and extract, then:
   cd dor
   ```

### Step 2: Set Up the Database

We'll use Docker to run PostgreSQL with pgvector (a special extension for AI document search):

```bash
# Start the database (this downloads and runs it automatically)
docker run --name pgvector-container -e POSTGRES_USER=langchain -e POSTGRES_PASSWORD=langchain -e POSTGRES_DB=langchain -p 6024:5432 -d pgvector/pgvector:pg16
```

**What this does:**
- Downloads and runs a PostgreSQL database with AI search capabilities
- Creates a database called "langchain" 
- Username: `langchain`, Password: `langchain`
- Runs on port 6024 (so it won't conflict with other databases)

**To check if it's working:**
```bash
docker ps
```
You should see `pgvector-container` in the list.

### Step 3: Install Project Dependencies

   ```bash
# Install all required packages
   uv sync
```

This downloads and installs everything the project needs to run.

### Step 4: Configure Your Settings

1. **Copy the example environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit the .env file:**
   Open the `.env` file in any text editor and add your information:
   ```env
   # Your Google Gemini API key (from Step 4 in prerequisites)
   GOOGLE_API_KEY=your_api_key_here
   
   # Database connection (use exactly this if you followed Step 2)
   POSTGRES_URL=postgresql://langchain:langchain@localhost:6024/langchain
   ```

### Step 5: Add Your PDF Documents

Copy your PDF files directly into the project folder (same folder as this README). The application will automatically find and process them.

```
dor/
├── your-document1.pdf     ← Put your PDFs here
├── your-document2.pdf     ← And here
├── important-report.pdf   ← And here
├── README.md
└── ... (other project files)
```

### Step 6: Process Your Documents

This step reads your PDFs and prepares them for searching:

```bash
# Process and index your PDF documents
uv run python src/index_documents.py
```

**What you'll see:**
```
INFO:__main__:Starting document indexing process...
INFO:__main__:Found 3 PDF files to index
INFO:__main__:Processing: your-document1.pdf
INFO:__main__:Split your-document1.pdf into 15 chunks
INFO:__main__:Successfully indexed 45 document chunks from 3 PDF files
```

### Step 7: Start Chatting!

   ```bash
# Start the chat interface
uv run python src/search_documents.py
   ```

**You'll see:**
```
============================================================
📚 Document Search Chat Interface
============================================================
Ask questions about your indexed documents!
Commands:
  - Type your question and press Enter
  - Type 'quit', 'exit', or 'q' to exit
  - Type 'help' for this message
============================================================

🤔 You: 
```

Now you can ask questions about your documents!

## Example Questions to Try 💬

- "What is this document about?"
- "Summarize the main points"
- "What are the key findings?"
- "What does it say about [specific topic]?"
- "Can you explain [concept from your document]?"
- "What recommendations are made?"

## Managing Your Database 🗄️

### Stop the database:
```bash
docker stop pgvector-container
```

### Start it again:
```bash
docker start pgvector-container
```

### Remove the database (if you want to start fresh):
```bash
docker stop pgvector-container
docker rm pgvector-container
# Then run the original docker run command again
```

## Troubleshooting 🔧

### "GOOGLE_API_KEY environment variable is required"
- Make sure you created the `.env` file
- Check that your API key is correctly pasted (no extra spaces)
- Get a new API key from [Google AI Studio](https://aistudio.google.com/app/apikey)

### "Failed to connect to vector store"
- Make sure Docker is running: `docker ps`
- If the container isn't running: `docker start pgvector-container`
- Check your POSTGRES_URL in the `.env` file

### "No PDF files found"
- Make sure your PDF files are in the main project folder (same level as README.md)
- Check that files end with `.pdf`
- Run the indexing step again: `uv run python src/index_documents.py`

### "Command not found: uv"
- Restart your terminal after installing uv
- Try the installation command again
- On Windows, make sure you're using PowerShell or Command Prompt

### Docker Issues
- **Windows**: Make sure Docker Desktop is running
- **Mac**: Make sure Docker Desktop is running
- **Linux**: Make sure Docker service is started: `sudo systemctl start docker`

### Chat Interface Not Working
- Make sure you ran the indexing step first
- Check that your database is running: `docker ps`
- Try restarting the database: `docker restart pgvector-container`

## Adding New Documents 📄

To add new PDF documents:

1. Copy new PDF files to the project folder
2. Run the indexing process again:
   ```bash
   uv run python src/index_documents.py
   ```
3. Start chatting with your updated document collection!

## What's Happening Behind the Scenes? 🔍

1. **Document Processing**: Your PDFs are split into small, searchable chunks
2. **AI Embeddings**: Each chunk gets converted into a mathematical representation
3. **Vector Storage**: These representations are stored in the PostgreSQL database
4. **Smart Search**: When you ask a question, the system finds the most relevant chunks
5. **AI Response**: Google's Gemini AI reads the relevant chunks and answers your question

## Need Help? 🆘

If you're stuck:
1. Check the troubleshooting section above
2. Make sure all prerequisites are installed
3. Verify your `.env` file has the correct API key and database URL
4. Check that your database container is running: `docker ps`

## Technical Details 🤓

For developers and technical users:

- **Frontend**: Command-line chat interface
- **Backend**: Python with LangChain and LangGraph
- **AI**: Google Gemini (LLM + Embeddings)
- **Database**: PostgreSQL with pgvector extension
- **Document Processing**: PyPDF with intelligent text splitting
- **Package Management**: uv (fast Python package manager)

---

**Enjoy chatting with your documents! 🎉**
