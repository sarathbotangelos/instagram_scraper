from instaloader import Profile
from src.app.instagram.client import get_instaloader
from src.app.core.config import settings


L = get_instaloader(settings.IG_USERNAME)

print(settings.IG_USERNAME)

profile = Profile.from_username(L.context, "rajivsurendra")

print(profile.username)
print(profile.full_name)
print(profile.followers)
