import instaloader


def get_loader() -> instaloader.Instaloader:
    """
    Returns a single Instaloader instance.

    Currently anonymous (no session).
    Safe for low-volume, chunked scraping.
    """

    L = instaloader.Instaloader(
        download_pictures=False,
        download_videos=False,
        download_video_thumbnails=False,
        save_metadata=False,
        compress_json=False,
    )

    return L
