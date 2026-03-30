import os
import hashlib
import logging
import praw
import pandas as pd
import datetime as dt
import requests
from typing import List, Optional
from dotenv import load_dotenv
from praw.models import MoreComments
import concurrent.futures

logger = logging.getLogger(__name__)


class RedditScraper:
    """Reddit subreddit scraper with quality filtering."""

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        user_agent: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        load_env: bool = True
    ):
        if load_env:
            load_dotenv()

        self.credentials = {
            'client_id': client_id or os.getenv('REDDIT_CLIENT_ID'),
            'client_secret': client_secret or os.getenv('REDDIT_CLIENT_SECRET'),
            'user_agent': user_agent or os.getenv('REDDIT_USER_AGENT', 'Rekomme:v1.0'),
        }

        # Only add username/password if both are present (for script auth)
        _username = username or os.getenv('REDDIT_USERNAME')
        _password = password or os.getenv('REDDIT_PASSWORD')
        if _username and _password:
            self.credentials['username'] = _username
            self.credentials['password'] = _password

        self.reddit = self._authenticate()

    def _authenticate(self) -> praw.Reddit:
        required_keys = ['client_id', 'client_secret', 'user_agent']
        for key in required_keys:
            if not self.credentials.get(key):
                raise ValueError(f"Missing Reddit API credential: {key}")

        try:
            reddit = praw.Reddit(**self.credentials)
            # Test the connection
            reddit.user.me()
            logger.info("Reddit authenticated successfully")
            return reddit
        except Exception as e:
            logger.warning(f"Script auth failed ({e}), trying read-only mode")
            # Fall back to read-only (no username/password)
            read_only_creds = {
                'client_id': self.credentials['client_id'],
                'client_secret': self.credentials['client_secret'],
                'user_agent': self.credentials['user_agent'],
            }
            return praw.Reddit(**read_only_creds)

    def scrape_subreddit(
        self,
        subreddit_name: str,
        sort_by: str = 'top',
        time_filter: str = 'year',
        limit: int = 1000,
        include_comments: bool = True,
        comments_limit: int = 15
    ) -> pd.DataFrame:
        try:
            subreddit = self.reddit.subreddit(subreddit_name)

            sorting_methods = {
                'top': subreddit.top(time_filter=time_filter, limit=limit),
                'hot': subreddit.hot(limit=limit),
                'new': subreddit.new(limit=limit),
                'rising': subreddit.rising(limit=limit)
            }

            posts = sorting_methods.get(sort_by.lower())
            if not posts:
                raise ValueError(f"Invalid sort method: {sort_by}")

            topics_data = []
            for submission in posts:
                body = submission.selftext or ""
                author = str(submission.author) if submission.author else "Deleted"

                # Skip deleted/removed posts
                if body in ('[deleted]', '[removed]'):
                    body = ""

                # Skip very low quality posts
                if submission.score < 2 and not body and submission.num_comments < 3:
                    continue

                comments = []
                if include_comments:
                    comments = self._extract_comments(submission, comments_limit)

                topics_data.append({
                    "title": submission.title,
                    "score": submission.score,
                    "id": submission.id,
                    "url": submission.url,
                    "comments_num": submission.num_comments,
                    "created": dt.datetime.fromtimestamp(submission.created),
                    "author": author,
                    "body": body,
                    "subreddit": subreddit_name,
                    "comments": comments,
                })

                if len(topics_data) >= limit:
                    break

            df = pd.DataFrame(topics_data)
            print(f"Scraped {len(df)} quality posts from r/{subreddit_name}")
            return df

        except Exception as e:
            logger.error(f"Error scraping r/{subreddit_name}: {e}")
            print(f"Error scraping {subreddit_name}: {e}")
            return pd.DataFrame()

    def _extract_comments(self, submission, comments_limit=15):
        """Extract top comments, filtering out bots and deleted."""
        try:
            submission.comments.replace_more(limit=0)
            comments = []
            for comment in submission.comments:
                if isinstance(comment, MoreComments):
                    continue

                text = comment.body
                author = str(comment.author) if comment.author else "Deleted"

                # Skip low quality comments
                if text in ('[deleted]', '[removed]', ''):
                    continue
                if author in ('AutoModerator', 'Deleted', '[deleted]'):
                    continue
                if len(text) < 15:
                    continue

                comments.append({
                    'text': text,
                    'score': comment.score,
                    'author': author
                })

            # Sort by score, keep top N
            comments.sort(key=lambda c: c['score'], reverse=True)
            return comments[:comments_limit]

        except Exception as e:
            logger.warning(f"Comment extraction failed: {e}")
            return []

    def save_to_file(
        self,
        dataframe: pd.DataFrame,
        base_filename: str = 'reddit_data',
        output_dir: str = 'output',
        formats: List[str] = ['csv', 'json']
    ) -> None:
        if dataframe.empty:
            print("No data to save.")
            return

        os.makedirs(output_dir, exist_ok=True)
        timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")

        for fmt in formats:
            try:
                filename = os.path.join(output_dir, f'{base_filename}_{timestamp}.{fmt}')
                if fmt == 'csv':
                    dataframe.to_csv(filename, index=False)
                elif fmt == 'json':
                    dataframe.to_json(filename, orient='records')
                print(f"Saved {fmt.upper()}: {filename}")
            except Exception as e:
                logger.error(f"Error saving {fmt}: {e}")

    def scrape_multiple_subreddits_concurrent(
        self,
        subreddits: List[str],
        sort_by: str = 'top',
        time_filter: str = 'year',
        limit: int = 500,
        max_workers: int = 4
    ) -> pd.DataFrame:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_subreddit = {
                executor.submit(
                    self.scrape_subreddit,
                    subreddit_name=subreddit,
                    sort_by=sort_by,
                    time_filter=time_filter,
                    limit=limit
                ): subreddit
                for subreddit in subreddits
            }

            combined_data = []
            for future in concurrent.futures.as_completed(future_to_subreddit):
                subreddit = future_to_subreddit[future]
                try:
                    data = future.result()
                    if not data.empty:
                        combined_data.append(data)
                except Exception as exc:
                    logger.error(f'r/{subreddit} failed: {exc}')

        if combined_data:
            result = pd.concat(combined_data, ignore_index=True)
            result = result.drop_duplicates(subset='id', keep='first')
            return result

        # Fallback: try OxyLabs web scraping if PRAW failed
        print("PRAW failed for all subreddits. Trying OxyLabs fallback...")
        return self._scrape_via_oxylabs(subreddits, limit)

    def _scrape_via_oxylabs(self, subreddits: List[str], limit: int = 100) -> pd.DataFrame:
        """Fallback scraper using OxyLabs when Reddit API returns 403."""
        username = os.getenv("OXYLABS_USERNAME")
        password = os.getenv("OXYLABS_PASSWORD")

        if not username or not password:
            print("OxyLabs credentials not set. Fallback failed.")
            return pd.DataFrame()

        all_posts = []
        for subreddit in subreddits:
            try:
                payload = {
                    "source": "universal",
                    "url": f"https://www.reddit.com/r/{subreddit}/top/.json?t=year&limit=100",
                    "render": "html",
                }
                resp = requests.post(
                    "https://realtime.oxylabs.io/v1/queries",
                    auth=(username, password),
                    json=payload,
                    timeout=60,
                )
                resp.raise_for_status()
                data = resp.json()

                # Parse Reddit JSON response
                results = data.get("results", [])
                if not results:
                    continue

                content = results[0].get("content", "")
                # Try to parse as JSON (Reddit .json endpoint)
                import json
                try:
                    reddit_data = json.loads(content)
                    children = reddit_data.get("data", {}).get("children", [])
                except Exception:
                    children = []

                for child in children[:limit]:
                    post = child.get("data", {})
                    if not post.get("title"):
                        continue

                    all_posts.append({
                        "title": post.get("title", ""),
                        "score": post.get("score", 0),
                        "id": post.get("id", hashlib.md5(post.get("title", "").encode()).hexdigest()[:12]),
                        "url": f"https://reddit.com{post.get('permalink', '')}",
                        "comments_num": post.get("num_comments", 0),
                        "created": dt.datetime.fromtimestamp(post.get("created_utc", 0)),
                        "author": post.get("author", "Deleted"),
                        "body": post.get("selftext", ""),
                        "subreddit": subreddit,
                        "comments": [],
                    })

                print(f"OxyLabs: scraped {len(children)} posts from r/{subreddit}")

            except Exception as e:
                logger.error(f"OxyLabs fallback failed for r/{subreddit}: {e}")
                continue

        if all_posts:
            df = pd.DataFrame(all_posts)
            df = df.drop_duplicates(subset='id', keep='first')
            return df
        return pd.DataFrame()
