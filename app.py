"""JobHunter AI entry point."""

from pathlib import Path

APP_NAME = "JobHunter AI"


def main():
    print(f"{APP_NAME} started")
    print(f"Project root: {Path(__file__).parent}")


if __name__ == "__main__":
    main()
