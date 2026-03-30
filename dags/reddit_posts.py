import os
from datetime import datetime
import psycopg2
from dotenv import load_dotenv
# Load environment variables from .env file
load_dotenv()
# Get PostgreSQL connection parameters from environment variables
db_host = os.getenv("POSTGRES_HOSTNAME")
db_name = os.getenv("POSTGRES_DB")
db_user = os.getenv("POSTGRES_USER")
db_password = os.getenv("POSTGRES_PASSWORD")
db_port = int(os.getenv("POSTGRES_PORT", "5432"))
def insert_source_reddit_post(post_id, source_url):
    """Insert initial Reddit post record with source URL"""
    conn = psycopg2.connect(
        host=db_host,
        database=db_name,
        user=db_user,
        password=db_password,
        port=db_port
    )
    cursor = conn.cursor()
    success = False
    try:
        # Create table if it doesn't exist with the new schema
        create_table_query = """
        CREATE TABLE IF NOT EXISTS reddit_posts (
            post_id TEXT PRIMARY KEY,
            source_url TEXT,
            processed_s3_url TEXT,
            created_date DATE,
            subreddit TEXT
        );
        """
        cursor.execute(create_table_query)
        # Insert post with source URL
        insert_query = """
        INSERT INTO reddit_posts (post_id, source_url)
        VALUES (%s, %s)
        ON CONFLICT (post_id) 
        DO UPDATE SET source_url = EXCLUDED.source_url;
        """
        
        cursor.execute(insert_query, (post_id, source_url))
        conn.commit()
        success = True
        
    except Exception as e:
        print(f"An error occurred inserting source Reddit post: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()
        
    return success
def update_processed_reddit_post(post_id, processed_data):
    """Update Reddit post record with processed data based on post_id"""
    conn = psycopg2.connect(
        host=db_host,
        database=db_name,
        user=db_user,
        password=db_password,
        port=db_port
    )
    cursor = conn.cursor()
    success = False
    try:
        update_query = """
        UPDATE reddit_posts 
        SET processed_s3_url = %s,
            subreddit = %s,
            created_date = %s
        WHERE post_id = %s
        """
        
        date_format = "%Y-%m-%d"
        raw_date = processed_data.get("created_date")
        if raw_date is None:
            raise ValueError("created_date is missing from processed_data")
        created_date = datetime.strptime(raw_date, date_format)
        
        cursor.execute(
            update_query, 
            (
                processed_data.get("processed_s3_url"),
                processed_data.get("subreddit"),
                created_date,
                post_id
            )
        )
        conn.commit()
        success = True
        
    except Exception as e:
        print(f"An error occurred updating processed Reddit post: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()
        
    return success
def get_all_reddit_posts():
    """Retrieve all Reddit posts from the database"""
    conn = psycopg2.connect(
        host=db_host,
        database=db_name,
        user=db_user,
        password=db_password,
        port=db_port
    )
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT post_id, source_url, processed_s3_url, subreddit, created_date FROM reddit_posts")
        results = cursor.fetchall()
        return results
    finally:
        cursor.close()
        conn.close()