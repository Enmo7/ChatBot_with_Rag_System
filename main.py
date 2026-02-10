import uvicorn
import os

# ✅ FIXED: 'if  name  ==  " main "' → 'if __name__ == "__main__"' (critical module guard corruption)
if __name__ == "__main__":
    print("🚀 Starting Enterprise RAG Server...")
    if not os.path.exists("./web"):
        print("❌ ERROR: 'web' folder missing! UI will not be available.")
        print("   → Create 'web' folder with index.html or disable static mounting in server.py")
    else:
        # ✅ FIXED: ' "server:app "' → 'server:app' (removed trailing space in module spec)
        # ✅ FIXED: 'host= "127.0.0.1 "' → 'host="127.0.0.1"' (removed space in string)
        uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)