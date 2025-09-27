# v1.1 RAG: Debug chunking strategy and test product discovery
import os
from dotenv import load_dotenv
from services.rag_service import RAGService
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

load_dotenv()

def debug_chunking_strategy():
    """Debug how the knowledge base is being chunked and why homeoffice queries fail."""
    print("🔍 DEBUGGING CHUNKING STRATEGY")
    print("=" * 60)

    try:
        # 1. Load and chunk the knowledge base manually to see the chunks
        print("1. Loading and chunking knowledge base...")

        loader = TextLoader("knowledge_base_techmarkt.txt", encoding='utf-8')
        documents = loader.load()

        text_splitter = RecursiveCharacterTextSplitter(
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

        chunks = text_splitter.split_documents(documents)

        print(f"   📊 Total chunks created: {len(chunks)}")

        print("\n2. Display all chunks and analyze chunking quality:")
        for i, chunk in enumerate(chunks):
            print(f"   Chunk {i+1}:")
            print(f"   " + "-"*50)
            print(f"{chunk.page_content}")  # Preserves original formatting including line breaks
            print(f"   " + "-"*50)
            print(f"   Length: {len(chunk.page_content)} characters\n")

        rag_service = RAGService()

        # Test queries that should find laptops for homeoffice
        test_queries = [
            "homeoffice setup ui ux designer",
            "laptop for work",
            "MacBook for designer",
            "computer for office",
            "Lenovo ThinkPad",
            "Apple MacBook Air"
        ]

        for query in test_queries:
            print(f"\n   🔍 Testing query: '{query}'")
            chunks_with_scores = rag_service.vectorstore.similarity_search_with_score(query, k=3)
            for i, (chunk, score) in enumerate(chunks_with_scores):
                print(f"\n       📄 Chunk {i+1} (Distance: {score:.6f}):")
                print(f"       " + "-"*60)
                print(f"{chunk.page_content}")
                print(f"       " + "-"*60)
        
        metadata = rag_service.vectorstore._collection.metadata
        print(f"Distance function: {metadata.get('hnsw:space', 'default_l2')}") 
        
        print(f"\n✅ Chunking analysis completed!")

    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_chunking_strategy()