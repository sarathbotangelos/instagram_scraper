from urllib.parse import urlparse
import instaloader

# reuse a single Instaloader context per process
_L = instaloader.Instaloader(
    download_pictures=False,
    download_videos=False,
    download_video_thumbnails=False,
    download_comments=False,
    save_metadata=False,
)


def resolve_username(entity_key: str) -> str | None:
    """
    Resolves an Instagram username from either:
    - a username
    - a profile URL
    - a post / reel / tv URL

    Returns username or None.
    """

    key = entity_key.strip()

    # -----------------------------
    # Case 1: already a username
    # -----------------------------
    if "/" not in key and "instagram.com" not in key:
        return key.lstrip("@")

    # -----------------------------
    # Case 2: profile URL
    # -----------------------------
    try:
        parsed = urlparse(key)
        if "instagram.com" in parsed.netloc:
            parts = [p for p in parsed.path.split("/") if p]

            # https://instagram.com/{username}
            if len(parts) == 1:
                return parts[0]

            # -----------------------------
            # Case 3: post / reel / tv URL
            # -----------------------------
            if parts[0] in {"p", "reel", "tv"} and len(parts) >= 2:
                shortcode = parts[1]
                post = instaloader.Post.from_shortcode(_L.context, shortcode)
                return post.owner_username
    except Exception:
        return None

    return None
