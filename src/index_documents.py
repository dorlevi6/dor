from langchain_text_splitters import CharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_postgres import PGVector
from dotenv import load_dotenv
import os
import asyncio
import logging
from pathlib import Path

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


async def index_documents() -> None:
    """
    Index all PDF documents in the workspace root directory.
    """
    try:
        logger.info("Starting document indexing process...")
        
        # Find all PDF files in the workspace root
        workspace_root = Path(".")
        pdf_files = list(workspace_root.glob("*.pdf"))
        
        if not pdf_files:
            logger.warning("No PDF files found in workspace root")
            return
        
        logger.info(f"Found {len(pdf_files)} PDF files to index")
        
        # Process each PDF file
        all_documents = []
        text_splitter = CharacterTextSplitter(
            separator="\n\n",
        )
        
        for pdf_file in pdf_files:
            try:
                logger.info(f"Processing: {pdf_file.name}")
                
                # Load the PDF
                loader = PyPDFLoader(str(pdf_file))
                documents = loader.load()
                
                # Split the documents into chunks
                splits = text_splitter.split_documents(documents)
                
                # Add metadata about the source file
                for split in splits:
                    split.metadata["source_file"] = pdf_file.name
                all_documents.extend(splits)
                logger.info(f"Split {pdf_file.name} into {len(splits)} chunks")
                
            except Exception as e:
                logger.error(f"Error processing {pdf_file.name}: {e}")
                continue
        
        if not all_documents:
            logger.warning("No documents were successfully processed")
            return
        
        # Check if documents are already indexed (simple check)
        try:
            # Try a simple similarity search to see if vector store has content
            test_results = vector_store.similarity_search("test query", k=1)
            if test_results:
                logger.info(f"Vector store already contains documents. Found {len(test_results)} existing documents.")
                # Optionally, you might want to skip re-indexing or clear and re-index
                # For now, we'll add new documents anyway
        except Exception:
            logger.info("Vector store appears to be empty, proceeding with indexing")
        
        # Add documents to vector store in batches
        batch_size = 10
        total_batches = (len(all_documents) + batch_size - 1) // batch_size
        
        for i in range(0, len(all_documents), batch_size):
            batch = all_documents[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            
            try:
                vector_store.add_documents(batch)
                logger.info(f"Added batch {batch_num}/{total_batches} ({len(batch)} documents)")
            except Exception as e:
                logger.error(f"Error adding batch {batch_num}: {e}")
                continue
        
        logger.info(f"Successfully indexed {len(all_documents)} document chunks from {len(pdf_files)} PDF files")
        
    except Exception as e:
        logger.error(f"Error during document indexing: {e}")
        raise


if __name__ == "__main__":
    # Allow running the indexing script directly
    asyncio.run(index_documents())