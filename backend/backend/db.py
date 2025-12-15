from pymongo import MongoClient
from backend.config import settings
import os

class Database:
    client: MongoClient = None
    
    @classmethod
    def connect_db(cls):
        """Connect to MongoDB"""
        cls.client = MongoClient(settings.MONGO_URI)
        print(f"Connected to MongoDB: {settings.DATABASE_NAME}")
    
    @classmethod
    def close_db(cls):
        """Close MongoDB connection"""
        if cls.client:
            cls.client.close()
            print("MongoDB connection closed")
    
    @classmethod
    def get_database(cls):
        """Get the database instance"""
        if cls.client is None:
            cls.connect_db()
        return cls.client[settings.DATABASE_NAME]

# Database collections helper
def get_collection(collection_name: str):
    """Get a specific collection from the database"""
    db = Database.get_database()
    return db[collection_name]
