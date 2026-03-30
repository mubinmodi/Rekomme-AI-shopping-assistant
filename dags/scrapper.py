import os
import time
from dotenv import load_dotenv

# Import custom modules
from reddit_scrapper import RedditScraper
from reddit_data_processor import RedditDataProcessor

def main():
    # Load environment variables
    load_dotenv()
    
    # Initialize scraper and processor
    scraper = RedditScraper()  # Use the new optimized class
    processor = RedditDataProcessor()
    
    # Subreddits to scrape
    subreddits = ['HeadphoneAdvice']
    
    # Scraping configuration
    scrape_config = {
        'sort_by': 'top',
        'time_filter': 'year',
        'limit': 5,
        'chunk_size': 250
    }
    
    try:
        # Use concurrent scraping method
        scraped_data = scraper.scrape_multiple_subreddits_concurrent(
            subreddits,
            sort_by=scrape_config['sort_by'],
            time_filter=scrape_config['time_filter'],
            limit=scrape_config['limit']
        )
        
        # Save full dataset
        scraper.save_to_file(
            scraped_data, 
            base_filename='multi_subreddit_posts', 
            output_dir='output', 
            formats=['csv', 'json']
        )
        
        # Process data in larger chunks
        for i in range(0, len(scraped_data), scrape_config['chunk_size']):
            chunk = scraped_data.iloc[i:i+scrape_config['chunk_size']]
            
            print(f"Processing chunk {i//scrape_config['chunk_size'] + 1}")
            processor.process_reddit_data(chunk)
            
            # Reduced delay between chunks
            time.sleep(1)
    
    except Exception as e:
        print(f"Error in main execution: {e}")

main()