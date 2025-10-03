from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
import chromadb
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# Configure service-specific logging (file logging only in development).
deployment_env = os.getenv("DEPLOYMENT_ENV", "development")

if deployment_env == "development":
    rag_handler = logging.FileHandler("logs/rag_service.log")
    rag_handler.setLevel(logging.INFO)
    rag_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    rag_handler.setFormatter(rag_formatter)
    logger.addHandler(rag_handler)

logger.setLevel(logging.INFO)

class RAGService:
    def __init__(self):
        '''Configure RAG service with LangChain retriever.'''
        
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

    def _initialize_retriever(self) -> None:
        # Initialize and configure retriever from vectorstore.
        self.retriever = self.vectorstore.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={"k": 3, "score_threshold": 0.3}
        )

    def load_chunk_store_knowledge(self, file_path: str = "prompts/knowledge_base_techmarkt.txt") -> None:
        '''Load, chunk and store the knowledge base using LangChain. Initialize the environment-based vectorstore and retriever.'''

        deployment_env = os.getenv("DEPLOYMENT_ENV", "development")
        collection_name = "techmarkt_knowledge_base"

        # Environment-aware ChromaDB client initialization.
        if deployment_env == "production":
            logger.info("Using Chroma Cloud (production mode)")
            chroma_client = chromadb.CloudClient(
                tenant=os.getenv("CHROMA_TENANT"),
                database=os.getenv("CHROMA_DATABASE"),
                api_key=os.getenv("CHROMA_API_KEY")
            )

            # Check if collection already exists with data.
            try:
                existing_collection = chroma_client.get_collection(name=collection_name)
                doc_count = existing_collection.count()

                if doc_count > 0:
                    logger.info(f"Collection '{collection_name}' already exists with {doc_count} documents. Skipping upload.")

                    # Connect to existing collection without re-uploading.
                    self.vectorstore = Chroma(
                        client=chroma_client,
                        collection_name=collection_name,
                        embedding_function=self.embeddings
                    )

                    # Initialize retriever.
                    self._initialize_retriever()

                    logger.info(f"Connected to existing knowledge base with {doc_count} chunks in production environment")
                    return

            except Exception:
                # Collection doesn't exist or error checking - proceed with upload.
                logger.info(f"Collection '{collection_name}' not found or empty. Creating and uploading knowledge base...")

        else:
            logger.info("Using local ChromaDB (development mode)")

            # Check if local collection already exists with data.
            persist_directory = "./chroma_db"
            if os.path.exists(persist_directory):
                try:
                    # Try to connect to existing local collection.
                    self.vectorstore = Chroma(
                        persist_directory=persist_directory,
                        collection_name=collection_name,
                        embedding_function=self.embeddings
                    )

                    # Check if collection has data.
                    doc_count = self.vectorstore._collection.count()

                    if doc_count > 0:
                        logger.info(f"Local collection '{collection_name}' already exists with {doc_count} documents. Skipping reload.")

                        # Initialize retriever.
                        self._initialize_retriever()

                        logger.info(f"Connected to existing local knowledge base with {doc_count} chunks in development environment")
                        return

                except Exception:
                    # Collection doesn't exist or error - proceed with upload.
                    logger.info(f"Local collection not found or empty. Creating and loading knowledge base...")

        # Load and split the knowledge base for RAG (first time only).
        loader = TextLoader(file_path, encoding='utf-8')
        documents = loader.load()
        intelligent_chunks = self.text_splitter.split_documents(documents)

        # Configure client based on environment.
        vectorstore_kwargs = {
            "documents": intelligent_chunks,
            "embedding": self.embeddings,
            "collection_name": collection_name,
            "collection_metadata": {"hnsw:space": "cosine"}
        }

        if deployment_env == "production":
            vectorstore_kwargs["client"] = chroma_client
        else:
            vectorstore_kwargs["persist_directory"] = "./chroma_db"

        # Initialize vectorstore with environment-specific configuration.
        self.vectorstore = Chroma.from_documents(**vectorstore_kwargs)

        # Initialize and configure retriever.
        self._initialize_retriever()

        logger.info(f"Knowledge base loaded with {len(intelligent_chunks)} chunks in {deployment_env} environment")

    def get_relevant_knowledge(self, user_message: str) -> Optional[str]:
        """Retrieve relevant knowledge and use the configured retriever.
        Args:
            user_message: User's question or message
        Returns:
            Formatted knowledge context for the LLM, or None if no relevant chunks.
        """
        
        retrieved_docs = self.retriever.invoke(user_message) # max. top 3 list of relevant documents with page_content and metadata
       
        if retrieved_docs:
            combined_knowledge = "\n\n".join(doc.page_content for doc in retrieved_docs) # relevant context for the chatbot to consider as one string

            # Log retrieval details for debugging and monitoring.
            logger.info(f"Retrieved {len(retrieved_docs)} chunks for query: '{user_message[:50]}{'...' if len(user_message) > 50 else ''}'")
            for i, doc in enumerate(retrieved_docs):
                chunk_preview = doc.page_content.replace('\n', ' ')[:80] + "..." if len(doc.page_content) > 80 else doc.page_content.replace('\n', ' ')
                logger.info(f"    Chunk {i+1}: {chunk_preview}")

            return combined_knowledge
        else:
            logger.warning(f"No relevant chunks found for query: '{user_message[:50]}{'...' if len(user_message) > 50 else ''}'")
            return None