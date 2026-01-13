import instaloader
from typing import List


def get_recent_post_urls(
    L: instaloader.Instaloader,
    username: str,
    max_posts: int = 12,
) -> List[str]:
    """
    Enumerates the most recent Instagram posts for a user.

    - Requires authenticated Instaloader context
    - Bounded by max_posts
    - No retries
    - No throttling
    - No job logic
    """

    profile = instaloader.Profile.from_username(L.context, username)

    post_urls: List[str] = []

    for idx, post in enumerate(profile.get_posts()):
        if idx >= max_posts:
            break

        post_urls.append(
            f"https://www.instagram.com/p/{post.shortcode}/"
        )

    return post_urls
