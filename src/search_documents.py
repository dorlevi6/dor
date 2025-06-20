from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_postgres import PGVector
from langgraph.graph import START, StateGraph
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from typing import List, TypedDict, Optional
from dotenv import load_dotenv
import os
import logging
import asyncio

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
POSTGRES_URL = os.getenv("POSTGRES_URL")

if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY environment variable is required")
if not POSTGRES_URL:
    raise ValueError("POSTGRES_URL environment variable is required")

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", api_key=GOOGLE_API_KEY)
embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004", api_key=GOOGLE_API_KEY)

prompt = PromptTemplate(
    template= """
You are a helpful and knowledgeable assistant. Use only the information provided in the "Context" section below to answer the user's question. If the answer cannot be found in the context, reply with "I don't know based on the provided information."

Context:
{retrieved_context}

Question:
{user_query}

Instructions:
- Base your answer strictly on the context above.
- If relevant, cite the specific part(s) of the context you used.
- If the answer is not present in the context, say "I don't know based on the provided information."
- Do not use any prior knowledge or make up information.""",
    input_variables=["retrieved_context", "user_query"],
)

try:
    vector_store = PGVector(
        connection=POSTGRES_URL,
        embeddings=embeddings,
        collection_name="documents",
    )
    logger.info("Successfully connected to vector store")
except Exception as e:
    logger.error(f"Failed to connect to vector store: {e}")
    raise

# Define state for application - Updated to include messages for chat interface compatibility
class State(TypedDict):
    messages: List[BaseMessage]
    question: Optional[str]
    context: Optional[List[Document]]
    answer: Optional[str]


# Define application steps
def extract_question(state: State) -> dict:
    """Extract the latest user question from messages."""
    messages = state["messages"]
    # Find the last human message
    for message in reversed(messages):
        if isinstance(message, HumanMessage):
            return {"question": message.content}
    
    # Fallback if no human message found
    return {"question": ""}


def retrieve(state: State) -> dict:
    """Retrieve relevant documents based on the question."""
    question = state.get("question", "")
    if not question:
        logger.warning("No question found for retrieval")
        return {"context": []}
    
    try:
        retrieved_docs = vector_store.similarity_search(question, k=5)
        logger.info(f"Retrieved {len(retrieved_docs)} documents for question: {question[:50]}...")
        return {"context": retrieved_docs}
    except Exception as e:
        logger.error(f"Error during retrieval: {e}")
        return {"context": []}


def generate(state: State) -> dict:
    """Generate answer based on retrieved context."""
    context = state.get("context", [])
    question = state.get("question", "")
    
    if not question:
        return {
            "answer": "I didn't receive a clear question. Please ask me something about the documents.",
            "messages": state["messages"] + [AIMessage(content="I didn't receive a clear question. Please ask me something about the documents.")]
        }
    
    if not context:
        return {
            "answer": "I don't know based on the provided information.",
            "messages": state["messages"] + [AIMessage(content="I don't know based on the provided information.")]
        }
    
    try:
        docs_content = "\n\n".join(doc.page_content for doc in context)
        messages = prompt.invoke({"retrieved_context": docs_content, "user_query": question})
        response = llm.invoke(messages)
        
        answer = response.content
        logger.info(f"Generated answer of length {len(answer)} for question: {question[:50]}...")
        
        return {
            "answer": answer,
            "messages": state["messages"] + [AIMessage(content=answer)]
        }
    except Exception as e:
        logger.error(f"Error during generation: {e}")
        error_msg = "I encountered an error while processing your question. Please try again."
        return {
            "answer": error_msg,
            "messages": state["messages"] + [AIMessage(content=error_msg)]
        }


# Compile application with proper sequence
graph_builder = StateGraph(State)
graph_builder.add_node("extract_question", extract_question)
graph_builder.add_node("retrieve", retrieve)
graph_builder.add_node("generate", generate)

graph_builder.add_edge(START, "extract_question")
graph_builder.add_edge("extract_question", "retrieve")
graph_builder.add_edge("retrieve", "generate")

graph = graph_builder.compile()


def print_welcome_message() -> None:
    """Print welcome message and instructions for the chat interface."""
    print("\n" + "="*60)
    print("📚 Document Search Chat Interface")
    print("="*60)
    print("Ask questions about your indexed documents!")
    print("Commands:")
    print("  - Type your question and press Enter")
    print("  - Type 'quit', 'exit', or 'q' to exit")
    print("  - Type 'help' for this message")
    print("="*60 + "\n")


def print_help() -> None:
    """Print help information."""
    print("\n" + "-"*40)
    print("Help:")
    print("  - Ask any question about your documents")
    print("  - The system will search for relevant information")
    print("  - Type 'quit', 'exit', or 'q' to exit")
    print("-"*40 + "\n")


async def run_chat_interface() -> None:
    """
    Run the interactive CLI chat interface.
    
    This function provides a continuous loop where users can ask questions
    about indexed documents. The conversation history is maintained throughout
    the session.
    """
    print_welcome_message()
    
    # Initialize conversation state
    messages: List[BaseMessage] = []
    
    try:
        while True:
            try:
                # Get user input
                user_input = input("🤔 You: ").strip()
                
                # Handle special commands
                if not user_input:
                    continue
                    
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("\n👋 Goodbye! Thanks for using the document search!")
                    break
                    
                if user_input.lower() == 'help':
                    print_help()
                    continue
                
                # Add user message to conversation
                messages.append(HumanMessage(content=user_input))
                
                # Create state for the graph
                state: State = {
                    "messages": messages,
                    "question": None,
                    "context": None,
                    "answer": None
                }
                
                print("🔍 Searching documents...")
                
                # Run the graph
                result = await asyncio.to_thread(graph.invoke, state)
                
                # Get the response
                answer = result.get("answer", "I couldn't generate an answer.")
                
                # Update messages with the result
                messages = result.get("messages", messages)
                
                # Display the response
                print(f"\n🤖 Assistant: {answer}\n")
                print("-" * 60)
                
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye! Thanks for using the document search!")
                break
                
            except Exception as e:
                logger.error(f"Error in chat interface: {e}")
                print(f"\n❌ Sorry, I encountered an error: {e}")
                print("Please try again or type 'quit' to exit.\n")
                
    except Exception as e:
        logger.error(f"Fatal error in chat interface: {e}")
        print(f"\n❌ Fatal error: {e}")
        print("Chat interface is shutting down.")


def main() -> None:
    """
    Main entry point for the chat interface.
    
    Checks if the vector store has documents and starts the chat interface.
    """
    try:
        # Test if the vector store has any documents
        test_results = vector_store.similarity_search("test", k=1)
        if not test_results:
            print("\n⚠️  Warning: No documents found in the vector store.")
            print("Please run the indexing script first to add documents:")
            print("python src/index_documents.py")
            return
            
        # Start the chat interface
        asyncio.run(run_chat_interface())
        
    except Exception as e:
        logger.error(f"Error starting chat interface: {e}")
        print(f"\n❌ Error: {e}")
        print("Make sure your database is running and documents are indexed.")


if __name__ == "__main__":
    main()