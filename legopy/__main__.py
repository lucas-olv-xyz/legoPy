"""CLI entry point so the app can be launched with python -m legopy."""

from .app import run_app


def main() -> None:
    run_app()


if __name__ == "__main__":
    main()
