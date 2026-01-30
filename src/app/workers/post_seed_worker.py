
import time
import json
import random
import requests
import traceback
from datetime import datetime, UTC
from typing import Optional, Dict, Tuple

from sqlalchemy.orm import Session
from src.app.core.db.models import User, PostsMetadata, ScrapeJob, ScrapeJobType, ScrapeJobStatus,PostMedia
from src.app.core.db.session import SessionLocal
from src.app.core.logging_config import logger
from src.app.instagram.client import build_authenticated_session
from src.app.services.email_service import send_alert_email
from src.app.services.extractors import extract_collaborators, extract_media_items

# Constants
# We will use this module-level logger which is configured in logging_config
# The user snippet used its own config, but we should adhere to project standards.

# User agents list for rotation (realistic browser headers)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
]

# Request headers template for realistic browser behavior
def get_browser_headers() -> Dict[str, str]:
    """Generate realistic browser headers with rotated User-Agent."""
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Cache-Control": "max-age=0",
        "Referer": "https://www.instagram.com/",
    }

def get_random_delay(min_seconds: float = 45, max_seconds: float = 240) -> float:
    """
    Generate random delay with jitter to appear more human-like.
    Range: 45-240 seconds (0.75-4 minutes) to simulate realistic browsing behavior.
    """
    return random.uniform(min_seconds, max_seconds)

def get_csrf_token(session: requests.Session) -> Optional[str]:
    """
    Safely extract csrftoken even if multiple exist for different domains/paths.
    """
    for cookie in session.cookies:
        if cookie.name == "csrftoken":
            return cookie.value
    return None

def refresh_csrf_token(session: requests.Session) -> bool:
    """
    Refresh CSRF token by visiting the main Instagram page.
    This prevents CSRF token expiry issues during long scraping sessions.
    Returns True if successful, False otherwise.
    """
    try:
        logger.info("Attempting to refresh CSRF token...")
        headers = get_browser_headers()
        response = session.get("https://www.instagram.com/", headers=headers, timeout=10)
        
        if response.status_code == 200:
            new_csrf = get_csrf_token(session)
            if new_csrf:
                logger.info(f"CSRF token refreshed successfully")
                return True
            else:
                logger.warning("CSRF token not found after refresh attempt")
                return False
        else:
            logger.warning(f"Failed to refresh CSRF token (status: {response.status_code})")
            return False
            
    except Exception as e:
        logger.error(f"Exception during CSRF token refresh: {e}")
        return False

def resolve_profile_id_graphql(session: requests.Session, username: str) -> Tuple[Optional[str], str]:
    """
    Alternative resolution using the web_profile_info query (GraphQL fallback).
    """
    logger.info(f"Trying GraphQL fallback for: {username}")
    url = "https://www.instagram.com/graphql/query/"
    params = {
        "query_hash": "69cba403172132360e0a52400795328d", # Common hash for web_profile_info
        "variables": json.dumps({"username": username})
    }
    
    headers = get_browser_headers()
    csrf = get_csrf_token(session)
    if csrf:
        headers["X-CSRFToken"] = csrf
    
    try:
        response = session.get(url, params=params, headers=headers, timeout=10)
        logger.info(f"GraphQL Fallback status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if "message" in data:
                logger.warning(f"Instagram message: {data['message']}")
                
            user = data.get("data", {}).get("user")
            if user and user.get("id"):
                return user["id"], "active"
                
            user = data.get("user")
            if user and user.get("id"):
                return user["id"], "active"
                
    except Exception as e:
        logger.error(f"GraphQL Fallback failed: {e}")
        
    return None, "empty_data"

def resolve_profile_id_search(session: requests.Session, username: str) -> Tuple[Optional[str], str]:
    """
    Third fallback using the search endpoint.
    """
    logger.info(f"Trying Search fallback for: {username}")
    url = f"https://www.instagram.com/web/search/topsearch/?context=blended&query={username}&rank_token=0.1"
    
    headers = get_browser_headers()
    
    try:
        response = session.get(url, headers=headers, timeout=10)
        logger.info(f"Search Fallback status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            for user_wrapper in data.get("users", []):
                user = user_wrapper.get("user")
                if user and user.get("username") == username:
                    return str(user.get("pk")), "active"
    except Exception as e:
        logger.error(f"Search Fallback failed: {e}")
        
    return None, "empty_data"

def resolve_profile_id(session: requests.Session, username: str) -> Tuple[Optional[str], str]:
    """
    Resolves Instagram User ID (PK) for a given username.
    Strategy 1: GET /{username}/?__a=1&__d=dis
    Strategy 2: GraphQL web_profile_info
    Strategy 3: Search endpoint
    """
    logger.info(f"Resolving profile ID for: {username}")
    url = f"https://www.instagram.com/{username}/?__a=1&__d=dis"
    
    # Get realistic headers
    headers = get_browser_headers()
    
    # Ensure CSRF token is in headers if present in cookies
    csrf = get_csrf_token(session)
    if csrf:
        headers["X-CSRFToken"] = csrf
    
    try:
        response = session.get(url, headers=headers, allow_redirects=False, timeout=10)
        logger.info(f"Resolution status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                profile_id = None
                if "graphql" in data and "user" in data["graphql"]:
                    profile_id = data["graphql"]["user"].get("id")
                elif "user" in data:
                    profile_id = data["user"].get("id")
                    
                if profile_id:
                    logger.info(f"Resolved profile_id via __a=1: {profile_id}")
                    return str(profile_id), "active"
            except Exception as e:
                logger.warning(f"Failed to parse __a=1 response: {e}")
    except Exception as e:
        logger.error(f"Resolution request failed: {e}")

    # 2. Try GraphQL fallback
    profile_id, status = resolve_profile_id_graphql(session, username)
    if profile_id:
        logger.info(f"Resolved profile_id via GraphQL: {profile_id}")
        return profile_id, "active"

    # 3. Try Search fallback
    profile_id, status = resolve_profile_id_search(session, username)
    if profile_id:
        logger.info(f"Resolved profile_id via Search: {profile_id}")
        return profile_id, "active"
        
    logger.error(f"All resolution methods failed for {username}")
    return None, "empty_data"

def fetch_posts_page(session: requests.Session, profile_id: str, cursor: str = None, retry_count: int = 0) -> Tuple[Optional[Dict], str]:
    """
    Using the stable REST API: GET https://www.instagram.com/api/v1/feed/user/{profile_id}/
    With retry logic for transient failures.
    """
    url = f"https://www.instagram.com/api/v1/feed/user/{profile_id}/"
    params = {
        "count": 12,
    }
    if cursor:
        params["max_id"] = cursor
    
    # Get fresh headers for each request
    headers = get_browser_headers()
    csrf = get_csrf_token(session)
    if csrf:
        headers["X-CSRFToken"] = csrf
        
    logger.info(f"Fetching posts for ID {profile_id} (cursor: {cursor})")
    
    try:
        response = session.get(url, params=params, headers=headers, timeout=15)
        
        if response.status_code in [401, 403]:
            logger.warning(f"Authentication error ({response.status_code}). Session may be dead.")
            return None, "session_dead"
        
        if response.status_code == 429:
            logger.warning("Rate limited (429). Too many requests.")
            return None, "rate_limited"
        
        if response.status_code >= 500:
            logger.warning(f"Server error ({response.status_code}). Retrying...")
            if retry_count < 2:
                time.sleep(random.uniform(5, 10))  # Brief backoff for server errors
                return fetch_posts_page(session, profile_id, cursor, retry_count + 1)
            return None, "server_error"
        
        res_json = response.json()
        if res_json.get("status") == "fail":
            message = res_json.get("message", "").lower()
            if "login_required" in message or "checkpoint" in message:
                logger.warning(f"Session issue: {message}")
                return None, "session_dead"
            logger.error(f"API Error: {res_json.get('message')}")
            return None, "error"
            
        return res_json, "active"
        
    except requests.exceptions.Timeout:
        logger.warning("Request timeout. Retrying...")
        if retry_count < 2:
            time.sleep(random.uniform(5, 10))
            return fetch_posts_page(session, profile_id, cursor, retry_count + 1)
        return None, "timeout"
        
    except requests.exceptions.ConnectionError:
        logger.warning("Connection error. Retrying...")
        if retry_count < 2:
            time.sleep(random.uniform(5, 10))
            return fetch_posts_page(session, profile_id, cursor, retry_count + 1)
        return None, "connection_error"
        
    except Exception as e:
        logger.error(f"Failed to parse REST response: {e}")
        return None, "empty_data"

def parse_and_persist_items(db: Session, user_db_id: int, items: list) -> int:
    """
    Parses items from v1 feed and persists to PostsMetadata.
    Returns count of new insertions.
    """
    count_new = 0
    
    for item in items:
        try:
            shortcode = item.get("code")
            if not shortcode:
                continue

            # Determine content kind and container status
            media_type = item.get("media_type") # 1=Img, 2=Vid, 8=Carousel
            product_type = item.get("product_type") # 'feed', 'clips', 'carousel_container'
            
            content_kind = "post"
            is_container = False
            
            if media_type == 8:
                is_container = True
                content_kind = "post" # Carousels are posts
            elif media_type == 2:
                # Video
                if product_type == "clips":
                    content_kind = "reel"
                else:
                    content_kind = "post" # Video Post
            elif media_type == 1:
                content_kind = "post"
                
            # Parse fields
            caption_text = None
            caption_obj = item.get("caption")
            if caption_obj:
                caption_text = caption_obj.get("text")
                
            timestamp = item.get("taken_at")
            posted_on = datetime.fromtimestamp(timestamp, UTC) if timestamp else None
            
            likes_count = item.get("like_count")
            comments_count = item.get("comment_count")
            views_count = item.get("view_count") or item.get("play_count") # view_count for vids


            # Extract collaborators
            collaborators_extracted = extract_collaborators(item)

            # Extract media items
            media_items = extract_media_items(item)
            
            # Check existing
            post = db.query(PostsMetadata).filter_by(shortcode=shortcode).first()
            if not post:
                post = PostsMetadata(
                    shortcode=shortcode,
                    posted_by=user_db_id,
                    content_kind=content_kind,
                    is_container=is_container,
                    collaborators=json.dumps(collaborators_extracted),
                    scraped_at=datetime.now(UTC),
                )
                db.add(post)
                count_new += 1
            
            # Update mutable fields
            post.caption = caption_text
            post.likes_count = likes_count
            post.comments_count = comments_count
            if views_count is not None:
                post.views_count = views_count
            if posted_on:
                post.posted_on = posted_on
                
            # If we wanted to parse media items (slides/URLs), we would do it here using PostMedia table.
            # For now, focusing on Metadata as per initial requirement/snippet.

            for media in media_items:
                existing_media = (
                    db.query(PostMedia)
                    .filter_by(
                        post_shortcode=shortcode,
                        media_index=media["media_index"],
                    )
                    .first()
                )

                if not existing_media:
                    existing_media = PostMedia(
                        post_shortcode=shortcode,
                        media_url=media["media_url"],
                        media_type=media["media_type"],
                        media_subtype=media["media_subtype"],
                        media_index=media["media_index"],
                        tagged_users=json.dumps(media["tagged_users"]),
                        scraped_at=datetime.now(UTC),
                    )
                    db.add(existing_media)
                else:
                    # update mutable fields on re-scrape
                    existing_media.media_url = media["media_url"]
                    existing_media.media_type = media["media_type"]
                    existing_media.media_subtype = media["media_subtype"]
                    existing_media.tagged_users = json.dumps(media["tagged_users"])
            
        except Exception as e:
            logger.error(f"Error parsing item {item.get('code', 'unknown')}: {e}")
            continue

    db.commit()
    return count_new

def seed_posts_for_user(db: Session, session: requests.Session, username: str):
    logger.info(f"=== Seeding posts for {username} ===")
    
    # Get the related ScrapeJob for this user
    scrape_job = (
        db.query(ScrapeJob)
        .filter(
            ScrapeJob.job_type == ScrapeJobType.PROFILE,
            ScrapeJob.entity_key == username
        )
        .first()
    )
    
    # Update job status to POSTS_SEED_RUNNING
    if scrape_job:
        scrape_job.status = ScrapeJobStatus.POSTS_SEED_RUNNING
        db.commit()
        logger.info(f"Updated job {scrape_job.id} to POSTS_SEED_RUNNING")
    
    # Resolve IG PK
    profile_id, status = resolve_profile_id(session, username)
    if status == "session_dead":
        error_msg = f"Session died during profile ID resolution for user: {username}"
        logger.critical(error_msg)
        send_alert_email(
            subject="Session Dead - Profile ID Resolution",
            body=f"<strong>Username:</strong> {username}<br><strong>Error:</strong> {error_msg}",
            error_details="Session became invalid while attempting to resolve Instagram profile ID. May need to re-authenticate."
        )
        if scrape_job:
            scrape_job.status = ScrapeJobStatus.POSTS_SEEDED_FAILED
            scrape_job.last_error = "Session dead during profile ID resolution"
            db.commit()
        raise RuntimeError("Session Dead")
    
    if not profile_id:
        logger.error(f"Could not resolve profile ID for {username}. Skipping.")
        if scrape_job:
            scrape_job.status = ScrapeJobStatus.POSTS_SEEDED_FAILED
            scrape_job.last_error = "Could not resolve profile ID"
            db.commit()
        return

    # Get DB user
    user_db = db.query(User).filter_by(username=username).first()
    if not user_db:
        logger.error(f"User {username} not in DB. Skipping.")
        if scrape_job:
            scrape_job.status = ScrapeJobStatus.POSTS_SEEDED_FAILED
            scrape_job.last_error = f"User {username} not found in database"
            db.commit()
        return

    # Pagination
    cursor = None
    has_next_page = True
    total_discovered = 0
    page_num = 1
    pages_processed = 0
    
    while has_next_page:
        page_data, status = fetch_posts_page(session, profile_id, cursor)
        
        if status == "session_dead":
            error_msg = f"Session died during pagination for user: {username}"
            logger.critical(error_msg)
            send_alert_email(
                subject="Session Dead - Posts Pagination",
                body=f"<strong>Username:</strong> {username}<br><strong>Page:</strong> {page_num}<br><strong>Total Posts Discovered:</strong> {total_discovered}<br><strong>Error:</strong> {error_msg}",
                error_details=f"Session became invalid while paginating through posts. Progress was lost at page {page_num} with {total_discovered} posts already discovered."
            )
            if scrape_job:
                scrape_job.status = ScrapeJobStatus.POSTS_SEEDED_FAILED
                scrape_job.last_error = "Session died during pagination"
                db.commit()
            raise RuntimeError("Session Dead")
        
        if status == "rate_limited":
            logger.warning(f"Rate limited while scraping {username}. Backing off for 60 seconds...")
            time.sleep(60)
            # Retry the current page
            continue
        
        if not page_data or "items" not in page_data:
            logger.warning(f"No items or error for {username} page {page_num}. Ending.")
            break
            
        items = page_data.get("items", [])
        new_count = parse_and_persist_items(db, user_db.id, items)
        
        total_discovered += len(items)
        logger.info(f"Page {page_num}: Found {len(items)} items ({new_count} new). Total so far: {total_discovered}")
        
        has_next_page = page_data.get("more_available", False)
        cursor = page_data.get("next_max_id")
        page_num += 1
        pages_processed += 1
        
        if has_next_page:
            # Adaptive delay: longer between pages to avoid detection
            sleep_time = get_random_delay(min_seconds=25, max_seconds=45)
            logger.info(f"Sleeping {sleep_time:.1f}s before next page...")
            time.sleep(sleep_time)
            
            # Refresh CSRF token every 5 pages to prevent expiry
            if pages_processed % 5 == 0:
                logger.info("Refreshing CSRF token as precaution...")
                refresh_csrf_token(session)

    logger.info(f"Finished {username}. Total posts processed: {total_discovered}")
    
    # Update job status to POSTS_SEEDED on success
    if scrape_job:
        scrape_job.status = ScrapeJobStatus.POSTS_SEEDED
        db.commit()
        logger.info(f"Updated job {scrape_job.id} to POSTS_SEEDED")





def run_worker():
    db = SessionLocal()

    # 1. Build authenticated session ONCE
    try:
        session = build_authenticated_session()
    except Exception as e:
        logger.critical(f"Failed to build authenticated session: {e}")
        db.close()
        return

    # # 2. Load users to process
    # users = db.query(User).all()


    # Load the records in scrape_jobs where job_type=PROFILE and status=USER_SEEDED
    users = (
        db.query(User)
        .join(
            ScrapeJob,
            (ScrapeJob.entity_key == User.username) &
            (ScrapeJob.job_type == ScrapeJobType.PROFILE) &
            (ScrapeJob.status == ScrapeJobStatus.USER_SEEDED)
        )
        .all()
    )

    logger.info(f"Found {len(users)} users in DB to process.")

    for i, user in enumerate(users):
        scrape_job = None
        try:
            # Get the job before processing
            scrape_job = (
                db.query(ScrapeJob)
                .filter(
                    ScrapeJob.job_type == ScrapeJobType.PROFILE,
                    ScrapeJob.entity_key == user.username
                )
                .first()
            )
            
            seed_posts_for_user(db, session, user.username)

        except RuntimeError as e:
            # Hard stop condition (checkpoint / login required)
            db.rollback()
            if "Session Dead" in str(e):
                error_msg = "Session marked dead. Stopping Instagram scraper worker immediately."
                logger.critical(error_msg)
                send_alert_email(
                    subject="Worker Stopped - Session Dead",
                    body=f"<strong>Current User:</strong> {user.username}<br><strong>Error:</strong> {error_msg}",
                    error_details="The authenticated Instagram session has died and cannot continue. The worker has stopped to prevent further failures. Manual re-authentication may be required."
                )
                break

            logger.error(
                f"Runtime error processing {user.username}: {e}"
            )
            if scrape_job:
                scrape_job.status = ScrapeJobStatus.POSTS_SEEDED_FAILED
                scrape_job.last_error = str(e)
                db.commit()

        except Exception as e:
            # Any DB / parsing / persistence error
            db.rollback()
            logger.error(
                f"Unexpected error processing {user.username}: {e}"
            )
            traceback.print_exc()
            if scrape_job:
                scrape_job.status = ScrapeJobStatus.POSTS_SEEDED_FAILED
                scrape_job.last_error = str(e)[:500]  # Truncate to avoid too long errors
                db.commit()

        # Controlled pacing between users (longer delay between different users)
        if i < len(users) - 1:
            sleep_time = get_random_delay(min_seconds=60, max_seconds=180)  # Longer delay between users: 1-3 minutes
            logger.info(f"Sleeping {sleep_time:.1f}s before next user...")
            time.sleep(sleep_time)

    db.close()
    logger.info("GraphQL post seeding worker finished.")

if __name__ == "__main__":
    run_worker()
