from langchain_text_splitters import CharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_postgres import PGVector
from dotenv import load_dotenv
import os
import asyncio
import logging
from pathlib import Path
import psycopg2
from psycopg2.extras import execute_values

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
POSTGRES_URL = os.getenv("POSTGRES_URL")

if not GOOGLE_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable is required")
if not POSTGRES_URL:
    raise ValueError("POSTGRES_URL environment variable is required")

embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004", api_key=GOOGLE_API_KEY)

try:
    vector_store = PGVector(
        connection=POSTGRES_URL,
        embeddings=embeddings,
        collection_name="documents",
    )
    logger.info("Successfully connected to vector store for indexing")
except Exception as e:
    logger.error(f"Failed to connect to vector store: {e}")
    raise

def create_chunks_table(conn):
    """
    Create the 'chunks' table with the required schema if it does not exist.
    Schema:
        1. id – unique identifier (SERIAL PRIMARY KEY)
        2. chunk_text – the text of the chunk
        3. embedding – the embedding vector
        4. filename – the original filename of the chunk
        5. split_strategy – the chunk splitting method used
        6. created_at – the timestamp when the row was inserted (default: NOW())
    """
    with conn.cursor() as cur:
        cur.execute('''
            CREATE TABLE IF NOT EXISTS chunks (
                id SERIAL PRIMARY KEY, -- Unique identifier for each chunk
                chunk_text TEXT NOT NULL, -- The text of the chunk
                embedding VECTOR, -- The embedding vector (use appropriate type for your PGVector extension)
                filename TEXT NOT NULL, -- The original filename of the chunk
                split_strategy TEXT NOT NULL, -- The chunk splitting method used
                created_at TIMESTAMP NOT NULL DEFAULT NOW() -- Timestamp when the row was inserted
            )
        ''')
        conn.commit()


def insert_chunks(conn, chunks, embeddings, filename, split_strategy):
    """
    Insert document chunks and their embeddings into the 'chunks' table.
    Each row will have all required fields populated.
    Args:
        conn: psycopg2 connection
        chunks: List of chunk texts
        embeddings: List of embedding vectors
        filename: The source filename for all chunks
        split_strategy: The splitting method used
    """
    values = [
        (chunk, embedding, filename, split_strategy)
        for chunk, embedding in zip(chunks, embeddings)
    ]
    with conn.cursor() as cur:
        execute_values(
            cur,
            '''
            INSERT INTO chunks (chunk_text, embedding, filename, split_strategy)
            VALUES %s
            ''',
            values
        )
        conn.commit()

async def index_documents() -> None:
    """
    Index all PDF documents in the workspace root directory.
    Ensures the 'chunks' table exists and inserts all required fields for each chunk.
    """
    try:
        logger.info("Starting document indexing process...")
        workspace_root = Path(".")
        pdf_files = list(workspace_root.glob("*.pdf"))
        if not pdf_files:
            logger.warning("No PDF files found in workspace root")
            return
        logger.info(f"Found {len(pdf_files)} PDF files to index")
        # Connect to PostgreSQL
        # psycopg2 does not support the '+psycopg' dialect in the connection string, so we remove it.
        conn_str = POSTGRES_URL.replace("+psycopg", "")
        conn = psycopg2.connect(conn_str)
        create_chunks_table(conn)  # Ensure table exists
        all_documents = []
        text_splitter = CharacterTextSplitter(separator="\n\n")
        split_strategy = "character"  # Or any other strategy you use
        for pdf_file in pdf_files:
            try:
                logger.info(f"Processing: {pdf_file.name}")
                loader = PyPDFLoader(str(pdf_file))
                documents = loader.load()
                splits = text_splitter.split_documents(documents)
                chunks = [split.page_content for split in splits]
                # Get embeddings for all chunks
                embeddings_model = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004", api_key=GOOGLE_API_KEY)
                embeddings = [embeddings_model.embed_query(chunk) for chunk in chunks]
                insert_chunks(conn, chunks, embeddings, pdf_file.name, split_strategy)
                logger.info(f"Inserted {len(chunks)} chunks from {pdf_file.name} into the database.")
            except Exception as e:
                logger.error(f"Error processing {pdf_file.name}: {e}")
                continue
        conn.close()
        logger.info(f"Successfully indexed document chunks from {len(pdf_files)} PDF files")
    except Exception as e:
        logger.error(f"Error during document indexing: {e}")
        raise


if __name__ == "__main__":
    # Allow running the indexing script directly
    asyncio.run(index_documents())