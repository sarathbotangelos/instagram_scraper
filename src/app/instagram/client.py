import instaloader

def get_instaloader(username: str):
    L = instaloader.Instaloader()
    L.load_session_from_file(
        username,   
        filename=f"/sessions/{username}.session"
    )
    return L
