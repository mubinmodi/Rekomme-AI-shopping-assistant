import os
import json
import traceback
from datetime import datetime
import pandas as pd
import time
import numpy as np

# LangChain imports
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore

# Additional imports
from pinecone import Pinecone, ServerlessSpec
import boto3
import psycopg2
from dotenv import load_dotenv

class NumpyEncoder(json.JSONEncoder):
    """
    Custom JSON encoder to handle NumPy arrays and other non-serializable types
    """
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        return super().default(obj)

class RedditDataProcessor:
    def __init__(self):
        """
        Initialize the RedditDataProcessor with necessary configurations and clients
        """
        # Load environment variables
        load_dotenv()
        
        # Initialize configuration
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.pinecone_api_key = os.getenv('PINECONE_API_KEY')
        self.pinecone_environment = os.getenv('PINECONE_ENVIRONMENT')
        self.pinecone_index_name = os.getenv('PINECONE_INDEX_NAME')
        
        # AWS S3 configuration
        self.aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
        self.aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        self.aws_s3_bucket = os.getenv('AWS_S3_BUCKET')
        
        # PostgreSQL configuration
        self.db_host = os.getenv("POSTGRES_HOSTNAME")
        self.db_name = os.getenv("POSTGRES_DB")
        self.db_user = os.getenv("POSTGRES_USER")
        self.db_password = os.getenv("POSTGRES_PASSWORD")
        self.db_port = int(os.getenv("POSTGRES_PORT", "5432"))
        
        # Initialize clients
        self._init_s3_client()
        self._init_pinecone()
        self._init_embedding_model()
        
    def _init_s3_client(self):
        """Initialize S3 client"""
        self.aws_region = os.getenv('AWS_REGION', 'us-east-1')
        self.s3_client = boto3.client(
            's3',
            region_name=self.aws_region,
            aws_access_key_id=self.aws_access_key,
            aws_secret_access_key=self.aws_secret_key
        )
    
    def _init_pinecone(self):
        """Initialize Pinecone client and index"""
        pc = Pinecone(
            api_key=self.pinecone_api_key
        )

        # Check existing indexes
        existing_indexes = pc.list_indexes().names()

        if self.pinecone_index_name not in existing_indexes:
            pc.create_index(
                name=self.pinecone_index_name, 
                dimension=1536, 
                metric='cosine',
                spec=ServerlessSpec(cloud="aws", region="us-east-1")
            )
            timeout = 60
            start = time.time()
            while not pc.describe_index(self.pinecone_index_name).status.ready:
                if time.time() - start > timeout:
                    raise TimeoutError("Pinecone index not ready after 60 seconds")
                time.sleep(1)

        self.pc_index = pc.Index(self.pinecone_index_name)
    
    def _init_embedding_model(self):
        """Initialize OpenAI embedding model"""
        self.embeddings = OpenAIEmbeddings(
            model='text-embedding-3-small'
        )
    
    
    def save_to_s3(self, content, filename):
        """
        Save content to S3 bucket
        
        Args:
            content (str): Content to save
            filename (str): Filename/key for S3 object
            
        Returns:
            str: S3 URL of saved object
        """
        try:
            # Use custom JSON encoder to handle non-serializable types
            serialized_content = json.dumps(content, cls=NumpyEncoder, default=str)
            
            self.s3_client.put_object(
                Bucket=self.aws_s3_bucket,
                Key=filename,
                Body=serialized_content.encode('utf-8'),
                ContentType='application/json'
            )
            return f"s3://{self.aws_s3_bucket}/{filename}"
        except Exception as e:
            print(f"Error uploading to S3: {e}")
            raise

    def _filter_post(self, row_dict):
        """Filter out low-quality posts."""
        body = row_dict.get('body', '')
        title = row_dict.get('title', '')
        score = row_dict.get('score', 0)

        # Skip deleted/removed posts with no comments
        if body in ('No body text', '[deleted]', '[removed]', ''):
            if not row_dict.get('comments'):
                return False

        # Skip posts with score < 1 (even author didn't upvote)
        if score < 1:
            return False

        # Skip posts with very short content and no comments
        total_text = f"{title} {body}"
        if len(total_text) < 50 and not row_dict.get('comments'):
            return False

        return True

    def _filter_comments(self, comments):
        """Keep only meaningful comments, sorted by score."""
        if not comments:
            return []

        filtered = []
        for c in comments:
            text = c.get('text', '')
            # Skip very short, deleted, or bot comments
            if len(text) < 20:
                continue
            if text in ('[deleted]', '[removed]'):
                continue
            if c.get('author', '') in ('AutoModerator', '[deleted]'):
                continue
            filtered.append(c)

        # Sort by score descending, keep top 10 most upvoted
        filtered.sort(key=lambda x: x.get('score', 0), reverse=True)
        return filtered[:10]

    def _build_chunks(self, row_dict):
        """
        Split a post into semantic chunks for better embeddings.
        - High-score comments (>5) get their own chunk with title context
        - Lower-score comments grouped in blocks of 2-3
        Returns list of (text, chunk_id) tuples.
        """
        title = row_dict.get('title', '')
        body = row_dict.get('body', '')
        post_id = row_dict.get('id', '')
        comments = self._filter_comments(row_dict.get('comments', []))

        chunks = []
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=80,
            separators=["\n\n", "\n", ". ", " "]
        )

        # Chunk 1: Title + Body
        main_text = f"Post: {title}\n\n{body}".strip()
        if len(main_text) > 80:
            body_chunks = splitter.split_text(main_text)
            for i, chunk in enumerate(body_chunks):
                chunks.append((chunk, f"{post_id}_body_{i}"))

        # High-score comments: individual chunks with title context
        high_score = [c for c in comments if c.get('score', 0) > 5]
        low_score = [c for c in comments if c.get('score', 0) <= 5]

        for i, c in enumerate(high_score):
            author = c.get('author', 'anon')
            text = c.get('text', '')
            score = c.get('score', 0)
            chunk_text = f"Re: {title}\nUser {author} (+{score}): {text}"
            chunks.append((chunk_text[:800], f"{post_id}_topcomment_{i}"))

        # Low-score comments: group in blocks of 3
        if low_score:
            block = ""
            block_idx = 0
            for i, c in enumerate(low_score):
                author = c.get('author', 'anon')
                text = c.get('text', '')
                score = c.get('score', 0)
                block += f"User {author} (+{score}): {text}\n\n"

                if (i + 1) % 3 == 0 or i == len(low_score) - 1:
                    if len(block) > 50:
                        chunk_text = f"Discussion on: {title}\n\n{block}"
                        sub_chunks = splitter.split_text(chunk_text)
                        for j, sc in enumerate(sub_chunks):
                            chunks.append((sc, f"{post_id}_comments_{block_idx}_{j}"))
                    block_idx += 1
                    block = ""

        # Fallback
        if not chunks and len(title) > 20:
            chunks.append((f"Post: {title}", f"{post_id}_title"))

        return chunks

    def _parse_epoch(self, created):
        """Convert created timestamp to epoch float for Pinecone filtering."""
        try:
            if isinstance(created, (int, float)):
                return float(created)
            if hasattr(created, 'timestamp'):
                return created.timestamp()
            return datetime.strptime(str(created), "%Y-%m-%d %H:%M:%S").timestamp()
        except Exception:
            return 0.0

    def process_reddit_data(self, dataframe):
        """
        Process Reddit data with quality filtering, semantic chunking,
        and batched embeddings for efficiency.
        """
        namespace = 'headphones'
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        vector_store = PineconeVectorStore(
            index=self.pc_index,
            embedding=self.embeddings,
            namespace=namespace
        )

        # Accumulate chunks across posts for batched embedding
        batch_texts = []
        batch_ids = []
        batch_metadatas = []
        BATCH_SIZE = 50

        total_chunks = 0
        skipped = 0

        for _, row in dataframe.iterrows():
            try:
                row_dict = row.to_dict()

                if 'comments' in row_dict:
                    row_dict['comments'] = [
                        {k: (v.tolist() if isinstance(v, np.ndarray) else v)
                         for k, v in comment.items()}
                        for comment in row_dict['comments']
                    ]

                if not self._filter_post(row_dict):
                    skipped += 1
                    continue

                s3_key = f"reddit_posts/{timestamp}/{row_dict['id']}.json"
                s3_url = self.save_to_s3(row_dict, s3_key)

                chunks = self._build_chunks(row_dict)
                if not chunks:
                    skipped += 1
                    continue

                # Metadata with epoch timestamp for recency filtering
                base_metadata = {
                    'id': row_dict['id'],
                    'title': row_dict['title'][:200],
                    'author': row_dict.get('author', 'unknown'),
                    'subreddit': row_dict.get('subreddit', ''),
                    'score': int(row_dict.get('score', 0)),
                    'created': str(row_dict.get('created', '')),
                    'created_epoch': self._parse_epoch(row_dict.get('created')),
                    's3_url': s3_url,
                    'namespace': namespace,
                }

                for text, chunk_id in chunks:
                    batch_texts.append(text)
                    batch_ids.append(chunk_id)
                    batch_metadatas.append(base_metadata.copy())

                total_chunks += len(chunks)

                # Flush batch when it reaches BATCH_SIZE
                if len(batch_texts) >= BATCH_SIZE:
                    vector_store.add_texts(texts=batch_texts, ids=batch_ids, metadatas=batch_metadatas)
                    print(f"Flushed batch of {len(batch_texts)} chunks to Pinecone")
                    batch_texts, batch_ids, batch_metadatas = [], [], []

                # Insert into database
                post_data = {
                    'id': row_dict['id'],
                    'title': row_dict['title'],
                    'body': row_dict.get('body', ''),
                    'author': row_dict.get('author', ''),
                    'subreddit': row_dict.get('subreddit', ''),
                    'score': row_dict.get('score', 0),
                    'created': row_dict.get('created', datetime.now()),
                    's3_url': s3_url,
                    'vector_id': f"{namespace}_{row_dict['id']}",
                    'namespace': namespace,
                    'comments': row_dict.get('comments', [])
                }
                self.insert_reddit_article(post_data)

            except Exception as e:
                print(f"Error processing post: {e}")
                traceback.print_exc()

        # Flush remaining chunks
        if batch_texts:
            vector_store.add_texts(texts=batch_texts, ids=batch_ids, metadatas=batch_metadatas)
            print(f"Flushed final batch of {len(batch_texts)} chunks to Pinecone")

        print(f"Done: {total_chunks} chunks embedded, {skipped} posts skipped")

    def insert_reddit_article(self, post_data):
        """
        Insert Reddit post data into PostgreSQL
        
        Args:
            post_data (dict): Dictionary containing post details
        
        Returns:
            bool: Success status of insertion
        """
        conn = None
        try:
            conn = psycopg2.connect(
                host=self.db_host,
                database=self.db_name,
                user=self.db_user,
                password=self.db_password,
                port=self.db_port
            )
            
            cursor = conn.cursor()
            
            # Ensure table exists
            create_table_query = """
            CREATE TABLE IF NOT EXISTS reddit_articles (
                id TEXT PRIMARY KEY,
                title TEXT,
                body TEXT,
                author TEXT,
                subreddit TEXT,
                score INTEGER,
                created_at TIMESTAMP,
                s3_url TEXT,
                vector_id TEXT,
                namespace TEXT,
                comments JSONB
            );
            """
            cursor.execute(create_table_query)
            
            # Insert or update post
            insert_query = """
            INSERT INTO reddit_articles
            (id, title, body, author, subreddit, score, created_at, s3_url, vector_id, namespace, comments)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
            title = EXCLUDED.title,
            body = EXCLUDED.body,
            score = EXCLUDED.score,
            s3_url = EXCLUDED.s3_url,
            vector_id = EXCLUDED.vector_id,
            namespace = EXCLUDED.namespace,
            comments = EXCLUDED.comments;
            """
            
            # Use the custom JSON encoder to handle NumPy types
            comments_json = json.dumps(post_data.get('comments', []), cls=NumpyEncoder)
            
            cursor.execute(insert_query, (
                post_data.get('id', ''),
                post_data.get('title', ''),
                post_data.get('body', ''),
                post_data.get('author', ''),
                post_data.get('subreddit', ''),
                post_data.get('score', 0),
                post_data.get('created', datetime.now()),
                post_data.get('s3_url', ''),
                post_data.get('vector_id', ''),
                post_data.get('namespace', ''),
                comments_json
            ))
            
            conn.commit()
            return True
        
        except Exception as e:
            print(f"Database insertion error: {e}")
            if conn:
                conn.rollback()
            return False
        
        finally:
            if conn:
                conn.close()