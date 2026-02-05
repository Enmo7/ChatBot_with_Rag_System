import uvicorn
import os

if __name__ == "__main__":
    print("🚀 Starting English-Optimized RAG Server...")
    print("🌍 URL: http://localhost:8000")
    
    if not os.path.exists("./web"):
        print("❌ Error: 'web' folder missing!")
    else:
        uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)