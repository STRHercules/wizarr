from app import create_app
import os

app = create_app()

if __name__ == "__main__":
    host = os.getenv("WIZARR_HOST", "0.0.0.0")
    port = int(os.getenv("WIZARR_PORT", "5690"))
    app.run(host=host, port=port)
