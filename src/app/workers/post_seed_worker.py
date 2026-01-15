
import time
import json
import logging
import requests
import traceback
from datetime import datetime, UTC
from typing import Optional, Dict, Any, Tuple

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from src.app.core.db.models import User, PostsMetadata
from src.app.core.db.session import SessionLocal
from src.app.core.logging_config import logger
from src.app.instagram.client import build_authenticated_session

# Constants
# We will use this module-level logger which is configured in logging_config
# The user snippet used its own config, but we should adhere to project standards.

def get_csrf_token(session: requests.Session) -> Optional[str]:
    """
    Safely extract csrftoken even if multiple exist for different domains/paths.
    """
    for cookie in session.cookies:
        if cookie.name == "csrftoken":
            return cookie.value
    return None

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
    
    try:
        response = session.get(url, params=params, timeout=10)
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
    
    try:
        response = session.get(url, timeout=10)
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
    
    # Ensure CSRF token is in headers if present in cookies
    csrf = get_csrf_token(session)
    if csrf:
        session.headers.update({"X-CSRFToken": csrf})
    
    session.headers.update({"Referer": "https://www.instagram.com/"})
    
    try:
        response = session.get(url, allow_redirects=False, timeout=10)
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

def fetch_posts_page(session: requests.Session, profile_id: str, cursor: str = None) -> Tuple[Optional[Dict], str]:
    """
    Using the stable REST API: GET https://www.instagram.com/api/v1/feed/user/{profile_id}/
    """
    url = f"https://www.instagram.com/api/v1/feed/user/{profile_id}/"
    params = {
        "count": 12,
    }
    if cursor:
        params["max_id"] = cursor
        
    logger.info(f"Fetching posts for ID {profile_id} (cursor: {cursor})")
    
    try:
        response = session.get(url, params=params, timeout=15)
        # logger.info(f"REST request status: {response.status_code}")
        
        if response.status_code in [401, 403]:
            return None, "session_dead"
        
        res_json = response.json()
        if res_json.get("status") == "fail":
            message = res_json.get("message", "").lower()
            if "login_required" in message or "checkpoint" in message:
                logger.warning(f"Session issue: {message}")
                return None, "session_dead"
            logger.error(f"API Error: {res_json.get('message')}")
            return None, "error"
            
        return res_json, "active"
    except Exception as e:
        logger.error(f"Failed to parse REST response: {e}")
        # logger.info(f"Raw response preview: {response.text[:500]}")
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
            
            # Check existing
            post = db.query(PostsMetadata).filter_by(shortcode=shortcode).first()
            if not post:
                post = PostsMetadata(
                    shortcode=shortcode,
                    posted_by=user_db_id,
                    content_kind=content_kind,
                    is_container=is_container,
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
            
        except Exception as e:
            logger.error(f"Error parsing item {item.get('code', 'unknown')}: {e}")
            continue

    db.commit()
    return count_new

def seed_posts_for_user(db: Session, session: requests.Session, username: str):
    logger.info(f"=== Seeding posts for {username} ===")
    
    # Resolve IG PK
    profile_id, status = resolve_profile_id(session, username)
    if status == "session_dead":
        logger.critical("Session appears dead. Stopping worker.")
        raise RuntimeError("Session Dead")
    
    if not profile_id:
        logger.error(f"Could not resolve profile ID for {username}. Skipping.")
        return

    # Get DB user
    user_db = db.query(User).filter_by(username=username).first()
    if not user_db:
        logger.error(f"User {username} not in DB. Skipping.")
        return

    # Pagination
    cursor = None
    has_next_page = True
    total_discovered = 0
    page_num = 1
    
    while has_next_page:
        page_data, status = fetch_posts_page(session, profile_id, cursor)
        
        if status == "session_dead":
            logger.critical("Session died during pagination user={username}")
            raise RuntimeError("Session Dead")
        
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
        
        if has_next_page:
            sleep_time = 12
            logger.info(f"Sleeping {sleep_time}s before next page...")
            time.sleep(sleep_time)

    logger.info(f"Finished {username}. Total posts processed: {total_discovered}")

def run_worker():
    db = SessionLocal()

    # 1. Build authenticated session ONCE
    try:
        session = build_authenticated_session()
    except Exception as e:
        logger.critical(f"Failed to build authenticated session: {e}")
        db.close()
        return

    # 2. Load users to process
    users = db.query(User).all()
    logger.info(f"Found {len(users)} users in DB to process.")

    for i, user in enumerate(users):
        try:
            seed_posts_for_user(db, session, user.username)

        except RuntimeError as e:
            # Hard stop condition (checkpoint / login required)
            db.rollback()
            if "Session Dead" in str(e):
                logger.critical(
                    "Session marked dead. Stopping GraphQL worker immediately."
                )
                break

            logger.error(
                f"Runtime error processing {user.username}: {e}"
            )

        except Exception as e:
            # Any DB / parsing / persistence error
            db.rollback()
            logger.error(
                f"Unexpected error processing {user.username}: {e}"
            )
            traceback.print_exc()

        # Controlled pacing between users
        if i < len(users) - 1:
            sleep_time = 5
            logger.info(f"Sleeping {sleep_time}s before next user...")
            time.sleep(sleep_time)

    db.close()
    logger.info("GraphQL post seeding worker finished.")

if __name__ == "__main__":
    run_worker()
