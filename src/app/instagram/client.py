import json
import requests
from requests.cookies import RequestsCookieJar


def build_authenticated_session() -> requests.Session:
    s = requests.Session()

    with open("cookies.json", "r") as f:
        cookies = json.load(f)

    with open("headers.json", "r") as f:
        headers = json.load(f)

    jar = RequestsCookieJar()
    for name, value in cookies.items():
        jar.set(
            name,
            value,
            domain=".instagram.com",
            path="/",
        )

    s.cookies = jar
    s.headers.update(headers)

    return s
