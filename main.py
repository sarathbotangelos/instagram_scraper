from scripts.seed_user import seed_user

if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        raise SystemExit("usage: python seed_user.py <instagram_username>")

    user = seed_user(sys.argv[1])
    print(f"Seeded user_id={user.id}")

