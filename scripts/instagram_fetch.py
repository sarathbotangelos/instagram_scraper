import instaloader

def fetch_profile(username: str):
    L = instaloader.Instaloader(
        download_pictures=False,
        download_videos=False,
        download_video_thumbnails=False,
        save_metadata=False,
        compress_json=False,
    )

    # OPTIONAL: reuse logged-in session
    # L.load_session_from_file("your_login_username")

    profile = instaloader.Profile.from_username(L.context, username)

    return {
        "username": profile.username,
        "full_name": profile.full_name,
        "bio": profile.biography,
        "followers": profile.followers,
        "following": profile.followees,
        "posts": profile.mediacount,
        "is_private": profile.is_private,
        "is_verified": profile.is_verified,
        "profile_pic_url": profile.profile_pic_url,
    }
