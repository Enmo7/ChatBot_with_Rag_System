import uvicorn
import os

if __name__ == "__main__":
    print("🚀 Starting Enterprise RAG Server...")
    if not os.path.exists("./web"):
        print("❌ Error: 'web' folder missing!")
    else:
        uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)