# v1.1 RAG: Investigate what similarity_score_threshold retriever actually calls
import os
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

load_dotenv()

def investigate_retriever_internals():
    """Investigate what the similarity_score_threshold retriever actually calls."""
    print("🔍 INVESTIGATING RETRIEVER INTERNALS")
    print("=" * 50)

    try:
        embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )

        vectorstore = Chroma(
            persist_directory="./chroma_db",
            embedding_function=embeddings,
            collection_name="techmarkt_knowledge_base"
        )

        test_query = "Samsung smartphone pricing"

        print(f"Query: '{test_query}'\n")

        # 1. Get the actual scores from each method
        print("1. Comparison of scoring methods:")

        print("   a) similarity_search_with_relevance_scores:")
        relevance_results = vectorstore.similarity_search_with_relevance_scores(test_query, k=3)
        for i, (doc, score) in enumerate(relevance_results):
            print(f"      {i+1}. Relevance: {score:.6f}")

        print("\n   b) similarity_search_with_score:")
        score_results = vectorstore.similarity_search_with_score(test_query, k=3)
        for i, (doc, score) in enumerate(score_results):
            print(f"      {i+1}. Distance: {score:.6f}")

        # 2. Test retriever behavior step by step
        print(f"\n2. Testing retriever with different thresholds:")

        thresholds = [0.05, 0.1, 0.15, 0.2, 0.3, 0.35, 0.4]
        for threshold in thresholds:
            retriever = vectorstore.as_retriever(
                search_type="similarity_score_threshold",
                search_kwargs={"k": 3, "score_threshold": threshold}
            )
            results = retriever.invoke(test_query)
            print(f"   Threshold {threshold}: {len(results)} results")

        # 3. Try to understand the conversion
        print(f"\n3. Score conversion analysis:")
        print("   If retriever uses relevance_scores:")
        for i, (doc, rel_score) in enumerate(relevance_results):
            print(f"   Result {i+1}: Relevance {rel_score:.6f} should pass threshold 0.1: {'YES' if rel_score >= 0.1 else 'NO'}")

        print("\n   If retriever uses distance scores:")
        for i, (doc, dist_score) in enumerate(score_results):
            converted = 1 - (dist_score / 2)  # Convert distance to relevance
            print(f"   Result {i+1}: Distance {dist_score:.6f} → Converted {converted:.6f} should pass threshold 0.1: {'YES' if converted >= 0.1 else 'NO'}")

        # 4. Check what happens with a very low threshold
        print(f"\n4. Testing very low threshold (0.01):")
        very_low_retriever = vectorstore.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={"k": 3, "score_threshold": 0.01}
        )
        very_low_results = very_low_retriever.invoke(test_query)
        print(f"   Results with 0.01 threshold: {len(very_low_results)}")

    except Exception as e:
        print(f"❌ Investigation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    investigate_retriever_internals()