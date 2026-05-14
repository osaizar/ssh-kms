import uvicorn

from .config import ADDR, PORT
from .main import app


def main():
    """Run the SSH KMS FastAPI application with Uvicorn."""
    uvicorn.run(app, host=ADDR, port=PORT)


if __name__ == "__main__":
    main()
