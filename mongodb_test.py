from pymongo import MongoClient

try:
    client = MongoClient("mongodb://localhost:27017/")
    db = client['artisan_marketplace']
    print("✅ MongoDB connected successfully:", db.name)
except Exception as e:
    print("❌ Connection failed:", e)


