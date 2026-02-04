import uvicorn
import os

if __name__ == "__main__":
    print("🚀 Starting FastAPI RAG Server...")
    print("📂 Frontend is served from ./web")
    print("🌍 Open your browser at: http://localhost:8000")
    
    # Ensure the web folder exists before running
    if not os.path.exists("./web"):
        print("❌ Error: 'web' folder not found! Please create it and add your HTML/CSS/JS files.")
    else:
        # Server Startup
        # host="0.0.0.0" Allows access from the local network
        # reload=True Allows automatic restart when code is modified
        uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)