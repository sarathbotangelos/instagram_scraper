import re

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_REGEX = re.compile(
    r"(?:\+?\d{1,3}[\s-]?)?(?:\(?\d{2,4}\)?[\s-]?)?\d{6,10}"
)

def extract_contacts(bio: str):
    emails = EMAIL_REGEX.findall(bio or "")
    phones = PHONE_REGEX.findall(bio or "")

    clean_bio = bio
    for e in emails:
        clean_bio = clean_bio.replace(e, "")
    for p in phones:
        clean_bio = clean_bio.replace(p, "")

    return {
        "email": emails[0] if emails else None,
        "phone": phones[0] if phones else None,
        "bio": clean_bio.strip(),
    }
