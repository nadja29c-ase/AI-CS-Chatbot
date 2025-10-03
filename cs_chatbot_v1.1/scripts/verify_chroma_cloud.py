import os
import sys
from dotenv import load_dotenv

# Add parent directory to path to import services.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.rag_service import RAGService

def verify_cloud_connection():
    """Verify Chroma Cloud connection and test retrieval"""

    load_dotenv()

    deployment_env = os.getenv("DEPLOYMENT_ENV", "development")
    print(f"\n=== Chroma Cloud Verification ===")
    print(f"Environment: {deployment_env}")

    if deployment_env != "production":
        print("⚠️  DEPLOYMENT_ENV is not set to 'production'")
        print("Set DEPLOYMENT_ENV=production in .env to test cloud connection")
        return

    # Check credentials
    required_vars = ["CHROMA_API_KEY", "CHROMA_TENANT", "CHROMA_DATABASE"]
    missing = [var for var in required_vars if not os.getenv(var)]

    if missing:
        print(f"❌ Missing credentials: {missing}")
        return

    print("✅ All credentials present")

    # Test RAG service initialization
    try:
        print("\n📦 Initializing RAG Service with Chroma Cloud...")
        rag = RAGService()
        print("✅ RAG Service initialized successfully")

        # Test retrieval
        test_queries = [
            "What smartphones do you sell?",
            "What is your return policy?",
            "Do you have laptops?"
        ]

        print("\n🔍 Testing retrievals:")
        for query in test_queries:
            result = rag.get_relevant_knowledge(query)
            if result:
                print(f"✅ '{query}' → Retrieved {len(result)} characters")
            else:
                print(f"⚠️  '{query}' → No results")

        print("\n✅ Chroma Cloud verification complete!")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_cloud_connection()