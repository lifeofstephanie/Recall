import os
import lancedb
from dotenv import load_dotenv

def reset_database():
    load_dotenv()
    
    db_uri = os.getenv("LANCE_DB_URI")
    api_key = os.getenv("LANCE_API_KEY")
    table_name = os.getenv("LANCE_TABLE_NAME", "movie_quotes")

    if not db_uri or not api_key:
        print("❌ Missing LanceDB credentials in .env")
        return

    print(f"Connecting to LanceDB Cloud at {db_uri}...")
    db = lancedb.connect(db_uri, api_key=api_key)
    
    try:
        db.drop_table(table_name)
        print(f"✅ Successfully deleted the '{table_name}' table and all its data.")
        print("You can now run ingest.py to start fresh with the Kaggle dataset.")
    except Exception as e:
        print(f"⚠️ Could not drop table '{table_name}'. It might already be empty or not exist. Error: {e}")

if __name__ == "__main__":
    reset_database()
