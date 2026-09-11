"""Vercel ASGI entrypoint; never write runtime data into the deployment."""
import os

os.environ["BACKEND_ONLY"] = "true"
os.environ["MEDSCAN_STORAGE"] = "postgres"

from server._core.env import env

# Reject an unsafe session-signing configuration before accepting requests.
_session_secret = env.cookie_secret

from server._core.main import app
