CREATE SCHEMA IF NOT EXISTS public;

CREATE SEQUENCE IF NOT EXISTS public.user_id_seq;
CREATE TABLE IF NOT EXISTS public.users (
    id INTEGER PRIMARY KEY DEFAULT nextval('public.user_id_seq'),
    username VARCHAR NOT NULL UNIQUE,
    password VARCHAR NOT NULL,
    email VARCHAR NOT NULL,
    full_name VARCHAR,
    active BOOLEAN DEFAULT TRUE,
    password_timestamp INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE SEQUENCE IF NOT EXISTS chat_session_id_seq;
CREATE TABLE IF NOT EXISTS public.chat_session (
    id INTEGER PRIMARY KEY DEFAULT nextval('chat_session_id_seq'),
    user_id INTEGER NOT NULL,
    title VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_message_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE SEQUENCE IF NOT EXISTS messages_id_seq;
CREATE TABLE IF NOT EXISTS public.messages (
    id INTEGER PRIMARY KEY DEFAULT nextval('messages_id_seq'),
    chat_session_id INTEGER NOT NULL,
    sender VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ref TEXT,
    tools_used TEXT
);

CREATE TABLE IF NOT EXISTS public.reddit_posts (
    post_id TEXT PRIMARY KEY,
    source_url TEXT,
    processed_s3_url TEXT,
    created_date DATE,
    subreddit TEXT
);
