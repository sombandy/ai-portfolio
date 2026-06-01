from src.mcp_server.config import configure_logging
from src.mcp_server.server import run_server


def main() -> None:
    configure_logging()
    run_server()


if __name__ == "__main__":
    main()
