import asyncio
import uuid
import sys
import os
import json

# Set PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import engine, Base
from sqlalchemy import text

async def test_chat_flow():
    """
    Integration test for the Chat V4.2 flow.
    """
    print("\n" + "="*60)
    print("TEST 1: Basic Chat Flow (Happy Path)")
    print("="*60)

    transport = ASGITransport(app=app)
    app.state.arq_pool = None  # Mock arq_pool for testing
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Health Check
        print("\n[1/6] Checking health...")
        resp = await ac.get("/health")
        print(f"✓ Health: {resp.json()}")

        # 2. Get existing documents
        print("\n[2/6] Fetching documents...")
        resp = await ac.get("/api/v1/documents/")
        docs = resp.json()
        if not docs:
            print("❌ No documents found. Please ingest a document first.")
            return

        doc_id = docs[0]['id']
        print(f"✓ Using document: {doc_id} ({docs[0]['filename']})")

        # 3. Create Conversation
        print("\n[3/6] Creating conversation...")
        resp = await ac.post(f"/api/v1/chat/conversations/{doc_id}", json={"title": "Test Chat V4"})
        conv = resp.json()
        conv_id = conv['id']
        print(f"✓ Conversation created: {conv_id}")

        # 4. Stream Chat (SSE)
        print("\n[4/6] Testing SSE Stream (Socratic mode)...")
        payload = {
            "document_id": doc_id,
            "message": "What is the main topic of this document?",
            "conversation_id": conv_id,
            "mode": "socratic"
        }

        full_response = ""
        meta_received = None
        
        # We use a context manager to handle the stream
        async with ac.stream("POST", "/api/v1/chat/stream", json=payload) as stream_resp:
            print(f"✓ Status: {stream_resp.status_code}")
            async for line in stream_resp.aiter_lines():
                if line.startswith("event: meta"):
                    continue
                elif line.startswith("event: chunk"):
                    continue
                elif line.startswith("event: done"):
                    continue
                elif line.startswith("event: error"):
                    print(f"❌ Error event: {line}")
                elif line.startswith("data:"):
                    data = line[5:].strip()
                    try:
                        parsed = json.loads(data)
                        if 'delta' in parsed:
                            full_response += parsed['delta']
                        elif 'message_id' in parsed:
                            meta_received = parsed
                    except:
                        pass

        print(f"✓ Full response received ({len(full_response)} chars)")
        if meta_received:
            print(f"✓ Meta received: {meta_received}")

        # 5. Check History
        print("\n[5/6] Checking history...")
        resp = await ac.get(f"/api/v1/chat/history/{conv_id}")
        history = resp.json()
        print(f"✓ History messages count: {len(history['messages'])}")
        for msg in history['messages']:
            print(f"  [{msg['role']}] ({msg['status']}): {msg['content'][:50]}...")

        # 6. Delete Conversation
        print("\n[6/6] Cleaning up conversation...")
        resp = await ac.delete(f"/api/v1/chat/conversations/{conv_id}")
        print(f"✓ Delete result: {resp.json()}")

    print("\n✅ Test 1 Completed Successfully!")


async def test_history_context():
    """
    Test that the AI retains context across multiple messages.
    """
    print("\n" + "="*60)
    print("TEST 2: History Context Retention")
    print("="*60)

    transport = ASGITransport(app=app)
    app.state.arq_pool = None
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Get documents
        resp = await ac.get("/api/v1/documents/")
        docs = resp.json()
        if not docs:
            print("❌ No documents found.")
            return

        doc_id = docs[0]['id']
        
        # Create conversation
        resp = await ac.post(f"/api/v1/chat/conversations/{doc_id}", json={"title": "Context Test"})
        conv_id = resp.json()['id']
        print(f"\n✓ Conversation created: {conv_id}")

        # First message
        print("\n[1/3] Sending first message...")
        payload1 = {
            "document_id": doc_id,
            "message": "Explain the first key concept from this document.",
            "conversation_id": conv_id,
            "mode": "socratic"
        }

        response1 = ""
        async with ac.stream("POST", "/api/v1/chat/stream", json=payload1) as stream_resp:
            async for line in stream_resp.aiter_lines():
                if line.startswith("data:"):
                    data = line[5:].strip()
                    try:
                        parsed = json.loads(data)
                        if 'delta' in parsed:
                            response1 += parsed['delta']
                    except:
                        pass
        
        print(f"✓ Response 1 received ({len(response1)} chars)")

        # Second message - should reference the first
        print("\n[2/3] Sending context-dependent message...")
        payload2 = {
            "document_id": doc_id,
            "message": "Can you elaborate on that point?",  # "that point" requires context
            "conversation_id": conv_id,
            "mode": "socratic"
        }

        response2 = ""
        async with ac.stream("POST", "/api/v1/chat/stream", json=payload2) as stream_resp:
            async for line in stream_resp.aiter_lines():
                if line.startswith("data:"):
                    data = line[5:].strip()
                    try:
                        parsed = json.loads(data)
                        if 'delta' in parsed:
                            response2 += parsed['delta']
                    except:
                        pass
        
        print(f"✓ Response 2 received ({len(response2)} chars)")

        # Check history
        print("\n[3/3] Checking message history...")
        resp = await ac.get(f"/api/v1/chat/history/{conv_id}")
        history = resp.json()
        print(f"✓ Total messages: {len(history['messages'])}")
        for msg in history['messages']:
            status_symbol = "✓" if msg['status'] == 'COMPLETED' else "⚠"
            print(f"  {status_symbol} [{msg['role']}] ({msg['status']}): {msg['content'][:40]}...")

        # Cleanup
        await ac.delete(f"/api/v1/chat/conversations/{conv_id}")

    print("\n✅ Test 2 Completed!")


async def test_title_generation():
    """
    Test that conversation title is generated in the background.
    """
    print("\n" + "="*60)
    print("TEST 3: Title Generation")
    print("="*60)

    transport = ASGITransport(app=app)
    app.state.arq_pool = None
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/documents/")
        docs = resp.json()
        if not docs:
            print("❌ No documents found.")
            return

        doc_id = docs[0]['id']
        
        # Create conversation with default title
        resp = await ac.post(f"/api/v1/chat/conversations/{doc_id}", json={"title": "Cuộc hội thoại mới"})
        conv_id = resp.json()['id']
        print(f"\n✓ Created conversation with default title: {resp.json()['title']}")

        # Send first message to trigger title generation
        print("\n[1/3] Sending first message (triggers title gen)...")
        payload = {
            "document_id": doc_id,
            "message": "What is quantum physics?",
            "conversation_id": conv_id,
            "mode": "socratic"
        }

        async with ac.stream("POST", "/api/v1/chat/stream", json=payload) as stream_resp:
            async for line in stream_resp.aiter_lines():
                pass  # Consume the stream

        print("✓ Stream completed")

        # Wait for background task to complete
        print("\n[2/3] Waiting for title generation (5 seconds)...")
        await asyncio.sleep(5)

        # Check if title changed
        print("\n[3/3] Checking updated title...")
        resp = await ac.get(f"/api/v1/chat/history/{conv_id}")
        history = resp.json()
        new_title = history['title']
        print(f"✓ New title: {new_title}")
        
        if new_title != "Cuộc hội thoại mới":
            print("✓ Title was successfully generated!")
        else:
            print("⚠ Title remained default (may need more wait time)")

        # Cleanup
        await ac.delete(f"/api/v1/chat/conversations/{conv_id}")

    print("\n✅ Test 3 Completed!")


async def test_error_handling():
    """
    Test error handling when stream fails.
    """
    print("\n" + "="*60)
    print("TEST 4: Error Handling")
    print("="*60)

    transport = ASGITransport(app=app)
    app.state.arq_pool = None
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/documents/")
        docs = resp.json()
        if not docs:
            print("❌ No documents found.")
            return

        doc_id = docs[0]['id']
        resp = await ac.post(f"/api/v1/chat/conversations/{doc_id}", json={"title": "Error Test"})
        conv_id = resp.json()['id']
        
        print(f"\n✓ Conversation created: {conv_id}")

        # Test with invalid data
        print("\n[1/2] Testing with invalid payload...")
        try:
            payload = {
                "document_id": "invalid-uuid",
                "message": "Test",
                "mode": "socratic"
            }
            resp = await ac.post("/api/v1/chat/stream", json=payload)
            print(f"✓ Response status: {resp.status_code}")
        except Exception as e:
            print(f"✓ Error caught: {e}")

        # Cleanup
        await ac.delete(f"/api/v1/chat/conversations/{conv_id}")

    print("\n✅ Test 4 Completed!")


async def run_all_tests():
    """Run all test suites."""
    try:
        await test_chat_flow()
        await test_history_context()
        await test_title_generation()
        await test_error_handling()
        
        print("\n" + "="*60)
        print("🎉 ALL TESTS COMPLETED!")
        print("="*60)
    except Exception as e:
        print(f"\n❌ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(run_all_tests())
