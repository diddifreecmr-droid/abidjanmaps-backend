import argparse
import hashlib
import secrets


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a service token and SHA-256 hash")
    parser.add_argument("--bytes", type=int, default=32, help="Random token size in bytes")
    args = parser.parse_args()

    token = secrets.token_urlsafe(args.bytes)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    print(f"SERVICE_TOKEN={token}")
    print(f"SERVICE_TOKEN_SHA256={token_hash}")


if __name__ == "__main__":
    main()
