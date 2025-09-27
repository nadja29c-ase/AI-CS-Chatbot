from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
import logging
import os
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Configure service-specific logging
rag_handler = logging.FileHandler("logs/rag_service.log")
rag_handler.setLevel(logging.INFO)
rag_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
rag_handler.setFormatter(rag_formatter)
logger.addHandler(rag_handler)
logger.setLevel(logging.INFO)

class RAGService:
    def __init__(self):
        # Configure RAG service with LangChain retriever.
        
        # Configuration of the embedding model that the vectorstore will use for converting text to vectors.
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )

        # Configuration of chunking strategy. Prepare docs for loading into vectorstore.
        self.text_splitter = RecursiveCharacterTextSplitter(
            separators=[
                "\n---",           # Major section breaks
                "\n\nQ:",          # FAQ questions
                "\n-",             # Product listings
                ":\n",             # Category headers
                "\n\n",            # Paragraph breaks
                "\n",              # Line breaks
                " ",               # Word breaks
            ],
            chunk_size=400,        # Target 200-400 tokens per chunk
            chunk_overlap=50,      # Small overlap for context continuity
            length_function=len,
        )
        self.load_chunk_store_knowledge()  # Load knowledge base on initialization

    def load_chunk_store_knowledge(self, file_path: str = "knowledge_base_techmarkt.txt") -> None:
        # Load, chunk and store the knowledge base using LangChain. Initialize the vectorstore and retriever.
        
        # Loading splitting the knowledge base for RAG.
        loader = TextLoader(file_path, encoding='utf-8')
        documents = loader.load()
        intelligent_chunks = self.text_splitter.split_documents(documents) #List of documents with page_content and metadata

        # Initialize vectorstore storage in chroma db. Store the intelligent chunks and convert them into vectors.
        self.vectorstore = Chroma.from_documents(
            documents=intelligent_chunks,
            embedding=self.embeddings, # convert text to vectors
            persist_directory="./chroma_db",
            collection_name="techmarkt_knowledge_base",
            collection_metadata={"hnsw:space": "cosine"} # use the cosine distance metric
        )

        # Initialize and configure retriever with the new vectorstore.
        self.retriever = self.vectorstore.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={"k": 3, "score_threshold": 0.3}  # Experimentally tuned threshold. Retriever expects relevance scores: lower = more relevant
        )

        logger.info(f"Knowledge base loaded with {len(intelligent_chunks)} chunks")

    def get_relevant_knowledge(self, user_message: str) -> Optional[str]:
        """Retrieve relevant knowledge and use the configured retriever.
        Args:
            user_message: User's question or message
        Returns:
            Formatted knowledge context for the LLM, or None if no relevant chunks.
        """
        
        retrieved_docs = self.retriever.invoke(user_message) # max. top 3 list of relevant documents with page_content and metadata
       
        if retrieved_docs:
            combined_knowledge = "\n\n".join(doc.page_content for doc in retrieved_docs) # relevant context for the chatbot to consider

            # Log retrieval details for debugging and monitoring
            logger.info(f"Retrieved {len(retrieved_docs)} chunks for query: '{user_message[:50]}{'...' if len(user_message) > 50 else ''}'")
            for i, doc in enumerate(retrieved_docs):
                chunk_preview = doc.page_content.replace('\n', ' ')[:80] + "..." if len(doc.page_content) > 80 else doc.page_content.replace('\n', ' ')
                logger.info(f"    Chunk {i+1}: {chunk_preview}")

            return combined_knowledge
        else:
            logger.warning(f"No relevant chunks found for query: '{user_message[:50]}{'...' if len(user_message) > 50 else ''}'")
            return None
        
            

            
        

