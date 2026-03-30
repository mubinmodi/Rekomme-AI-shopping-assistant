import os
import time
import pandas as pd
from datetime import timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago

# Import custom modules
from reddit_scrapper import RedditScraper
from reddit_data_processor import RedditDataProcessor

def scrape_reddit(**kwargs):
    """
    Scrape Reddit data using RedditScraper
    """
    scraper = RedditScraper()

    subreddits = ['HeadphoneAdvice']

    scrape_config = {
        'sort_by': 'top',
        'time_filter': 'year',
        'limit': 1000
    }

    try:
        scraped_data = scraper.scrape_multiple_subreddits_concurrent(
            subreddits,
            sort_by=scrape_config['sort_by'],
            time_filter=scrape_config['time_filter'],
            limit=scrape_config['limit']
        )

        scraper.save_to_file(
            scraped_data,
            base_filename='multi_subreddit_posts',
            output_dir='output',
            formats=['csv', 'json']
        )

        return scraped_data.to_json(orient='records')

    except Exception as e:
        print(f"Error in scraping execution: {e}")
        raise

def process_reddit_data(**kwargs):
    """
    Process scraped Reddit data using RedditDataProcessor
    """
    # Pull scraped data from XCom
    ti = kwargs['ti']
    scraped_json = ti.xcom_pull(task_ids='scrape_task')

    if not scraped_json:
        print("No data to process")
        return

    scraped_data = pd.read_json(scraped_json, orient='records')

    if scraped_data.empty:
        print("No data to process")
        return
    
    # Initialize processor
    processor = RedditDataProcessor()
    
    # Process data in larger chunks
    scrape_config = {
        'chunk_size': 250
    }
    
    try:
        for i in range(0, len(scraped_data), scrape_config['chunk_size']):
            chunk = scraped_data.iloc[i:i+scrape_config['chunk_size']]
            
            print(f"Processing chunk {i//scrape_config['chunk_size'] + 1}")
            processor.process_reddit_data(chunk)
            
            # Reduced delay between chunks
            time.sleep(1)
    
    except Exception as e:
        print(f"Error in processing execution: {e}")
        raise

# DAG configuration
with DAG(
    'reddit_data_pipeline',
    start_date=days_ago(1),
    schedule=None,
    dagrun_timeout=timedelta(minutes=500),
    # execution_timeout=timedelta(minutes=200),
    catchup=False,
    default_args={
        'owner': 'airflow',
        'retries': 1,
        'retry_delay': timedelta(minutes=5),
    
    }
) as dag:
    
    scrape_task = PythonOperator(
        task_id='scrape_task',
        python_callable=scrape_reddit,
        provide_context=True
    )
    
    process_task = PythonOperator(
        task_id='process_task',
        python_callable=process_reddit_data,
        provide_context=True
    )
    
    # Set task dependencies
    scrape_task >> process_task
