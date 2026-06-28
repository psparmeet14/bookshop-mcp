import http.server
import os
import secrets
import threading
import urllib.parse
import webbrowser

import httpx
from mcp.server.fastmcp import FastMCP

BOOKSHOP_BASE_URL = "http://localhost:8080"
CALLBACK_PORT = 9000
CALLBACK_URI = f"http://localhost:{CALLBACK_PORT}/callback"
CLIENT_ID = "bookshop-mcp"
CLIENT_SECRET = os.environ.get("BOOKSHOP_MCP_CLIENT_SECRET", "mcp-secret")

mcp = FastMCP("bookshop")


def _oauth_browser_flow() -> str | dict:
    """
    Full OAuth 2.0 Authorization Code Flow:
    1. Opens the bookshop consent page in the system browser.
    2. Listens on localhost:9000/callback for the redirect.
    3. Exchanges the auth code for a Bearer token.
    Returns the token string, or an error dict.
    """
    state = secrets.token_urlsafe(16)
    result = {}

    class CallbackHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            result["code"] = params.get("code", [None])[0]
            result["state"] = params.get("state", [None])[0]

            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"""
                <html><body style="font-family:system-ui;text-align:center;padding-top:60px">
                <h2>&#10003; Authorization complete</h2>
                <p>You can close this tab and return to Claude.</p>
                </body></html>
            """)

        def log_message(self, *args):
            pass  # suppress server access logs

    # Start a one-shot local server to catch the redirect
    server = http.server.HTTPServer(("localhost", CALLBACK_PORT), CallbackHandler)
    thread = threading.Thread(target=server.handle_request)
    thread.daemon = True
    thread.start()

    # Open the bookshop consent page in the user's default browser
    authorize_url = (
        f"{BOOKSHOP_BASE_URL}/oauth/authorize"
        f"?response_type=code"
        f"&client_id={CLIENT_ID}"
        f"&redirect_uri={urllib.parse.quote(CALLBACK_URI)}"
        f"&scope=books:read+profile:read"
        f"&state={state}"
    )
    webbrowser.open(authorize_url)

    # Wait up to 2 minutes for the user to log in
    thread.join(timeout=120)
    server.server_close()

    if not result.get("code"):
        return {"error": "Authorization timed out or was cancelled."}
    if result.get("state") != state:
        return {"error": "State mismatch — possible CSRF. Please try again."}

    # Exchange the auth code for a JWT
    token_resp = httpx.post(
        f"{BOOKSHOP_BASE_URL}/oauth/token",
        data={
            "grant_type": "authorization_code",
            "code": result["code"],
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uri": CALLBACK_URI,
        },
    )
    token_resp.raise_for_status()
    return token_resp.json()["access_token"]


@mcp.tool()
def list_books() -> list[dict]:
    """List all books in the public catalog (no login required)."""
    response = httpx.get(f"{BOOKSHOP_BASE_URL}/books")
    response.raise_for_status()
    return response.json()


@mcp.tool()
def get_my_books() -> dict:
    """
    Get your personalized book list via OAuth 2.0.

    Opens the Bookshop sign-in page in your browser — you log in there.
    Your credentials never pass through Claude.
    After you approve, this tool fetches only the books you have access to.

    Named users to try: alice (password: alice123) or bob (password: bob123)
    """
    token = _oauth_browser_flow()
    if isinstance(token, dict):
        return token  # propagate error

    response = httpx.get(
        f"{BOOKSHOP_BASE_URL}/me/books",
        headers={"Authorization": f"Bearer {token}"},
    )
    response.raise_for_status()
    data = response.json()

    # Resolve who is logged in from /me/profile
    profile_resp = httpx.get(
        f"{BOOKSHOP_BASE_URL}/me/profile",
        headers={"Authorization": f"Bearer {token}"},
    )
    username = profile_resp.json().get("username", "unknown") if profile_resp.is_success else "unknown"

    return {
        "user": username,
        "books": data["content"],
        "total": data["page"]["totalElements"],
        "page": data["page"],
        "_links": data["_links"],
    }


@mcp.tool()
def get_my_profile() -> dict:
    """
    Get your profile (who am I) via OAuth 2.0.
    Opens the Bookshop sign-in page in your browser — credentials never pass through Claude.
    """
    token = _oauth_browser_flow()
    if isinstance(token, dict):
        return token

    response = httpx.get(
        f"{BOOKSHOP_BASE_URL}/me/profile",
        headers={"Authorization": f"Bearer {token}"},
    )
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    mcp.run(transport="stdio")
