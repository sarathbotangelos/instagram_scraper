# import instaloader
# from typing import List


# def get_recent_post_urls(
#     L: instaloader.Instaloader,
#     username: str,
#     max_posts: int = 12,
# ) -> List[str]:
#     """
#     Enumerates the most recent Instagram posts for a user.

#     - Requires authenticated Instaloader context
#     - Bounded by max_posts
#     - No retries
#     - No throttling
#     - No job logic
#     """

#     profile = instaloader.Profile.from_username(L.context, username)

#     post_urls: List[str] = []

#     for idx, post in enumerate(profile.get_posts()):
#         if idx >= max_posts:
#             break

#         post_urls.append(
#             f"https://www.instagram.com/p/{post.shortcode}/"
#         )

#     return post_urls



import json
import requests
from typing import List
import instaloader


def get_recent_post_urls(
    L: instaloader.Instaloader,
    username: str,
    max_posts: int = 12,
) -> List[str]:
    """
    Fetch recent Instagram post URLs using web_profile_info endpoint.

    - Uses authenticated cookies from Instaloader session
    - Avoids GraphQL doc_id
    - Single request
    - Bounded by max_posts
    """

    session = L.context._session  # requests.Session with cookies loaded

    headers = {
        "User-Agent": L.context.user_agent,
        "X-IG-App-ID": "936619743392459",
        "Accept": "application/json",
        "Referer": f"https://www.instagram.com/{username}/",
    }

    url = "https://www.instagram.com/api/v1/users/web_profile_info/"

    resp = session.get(
        url,
        headers=headers,
        params={"username": username},
        timeout=15,
    )

    resp.raise_for_status()

    payload = resp.json()

    user = payload["data"]["user"]
    edges = user["edge_owner_to_timeline_media"]["edges"]

    post_urls: List[str] = []

    for edge in edges[:max_posts]:
        shortcode = edge["node"]["shortcode"]
        post_urls.append(f"https://www.instagram.com/p/{shortcode}/")

    return post_urls
