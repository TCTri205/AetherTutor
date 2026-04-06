import httpx
import asyncio
import json

BASE_URL = "http://localhost:8000"

async def test_pipeline():
    async with httpx.AsyncClient(timeout=60.0) as client:
        # 1. Test Ingest
        print("--- Testing Ingest ---")
        ingest_payload = {
            "content": "Albert Einstein was a German-born theoretical physicist. He is best known for developing the theory of relativity. He worked at Princeton University.",
            "filename": "einstein_test.txt"
        }
        
        try:
            response = await client.post(f"{BASE_URL}/api/v1/documents/test-ingest", json=ingest_payload)
            print(f"Ingest Response: {response.status_code}, {response.json()}")
            
            if response.status_code != 201:
                return

            doc_id = response.json()["document_id"]

            # 2. Test Query
            print("\n--- Testing Query ---")
            query_payload = {
                "document_id": doc_id,
                "query": "Who is Albert Einstein and where did he work?"
            }
            response = await client.post(f"{BASE_URL}/api/v1/graph/query", json=query_payload)
            print(f"Query Response: {response.status_code}")
            if response.status_code == 200:
                print(f"AI Answer: {response.json()['response']}")
                print(f"Context Pieces: {len(response.json()['context_used'])}")

            # 3. Test Duplicate Ingest
            print("\n--- Testing Duplicate Ingest (Idempotency) ---")
            response = await client.post(f"{BASE_URL}/api/v1/documents/test-ingest", json=ingest_payload)
            print(f"Duplicate Ingest Response: {response.status_code}, {response.json()}")

        except Exception as e:
            print(f"Error during validation: {e}")

if __name__ == "__main__":
    asyncio.run(test_pipeline())
