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

def fetch_posts(username: str, count: int = 12):
    L = instaloader.Instaloader(
        download_pictures=False,
        download_videos=False,
        download_video_thumbnails=False,
        save_metadata=False,
        compress_json=False,
    )
    
    profile = instaloader.Profile.from_username(L.context, username)
    posts = []
    
    for i, post in enumerate(profile.get_posts()):
        if i >= count:
            break
            
        post_data = {
            "shortcode": post.shortcode,
            "posted_on": post.date_utc,
            "caption": post.caption,
            "likes": post.likes,
            "comments": post.comments,
            "views": post.video_view_count if post.is_video else 0,
            "content_kind": "reel" if post.is_video and post.typename == 'GraphVideo' else "post",
            "is_container": post.typename == 'GraphSidecar',
            "collaborators": [c.username for c in post.collaborators] if getattr(post, 'collaborators', None) else [],
            "media": []
        }
        
        if post.typename == 'GraphSidecar':
            for idx, sidecar_node in enumerate(post.get_sidecar_nodes()):
                tags = []
                try:
                    tags = [u.user.username for u in getattr(sidecar_node, 'tagged_users', [])]
                except (AttributeError, TypeError):
                    pass
                    
                post_data["media"].append({
                    "url": sidecar_node.display_url if not sidecar_node.is_video else sidecar_node.video_url,
                    "type": "video" if sidecar_node.is_video else "image",
                    "index": idx,
                    "tagged_users": tags
                })
        else:
            tags = []
            try:
                tags = [u.user.username for u in getattr(post, 'tagged_users', [])]
            except (AttributeError, TypeError):
                pass
                
            post_data["media"].append({
                "url": post.url if not post.is_video else post.video_url,
                "type": "video" if post.is_video else "image",
                "index": 0,
                "tagged_users": tags
            })
            
        posts.append(post_data)
        
    return posts
