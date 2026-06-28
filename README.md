# 📚 Bookshop MCP Server

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that connects AI assistants (like Claude) to a bookshop backend. It enables secure browsing of the public book catalog and authenticated access to personalized user data via **OAuth 2.0 Authorization Code Flow**.

---

## ✨ Features

- 📖 **List all books** from the public catalog — no login required.
- 🔐 **Access your personal book list** securely via OAuth 2.0.
- 👤 **View your profile** (who am I?) via OAuth 2.0.
- 🛡️ **Credentials never pass through the AI** — users authenticate directly in their browser.
- 🔒 **CSRF protection** using a `state` token on every OAuth flow.

---

## 🛠️ Available Tools

| Tool | Description | Auth Required |
|------|-------------|:---:|
| `list_books` | Lists all books in the public catalog | ❌ |
| `get_my_books` | Fetches the logged-in user's personalized book list | ✅ OAuth 2.0 |
| `get_my_profile` | Returns the logged-in user's profile information | ✅ OAuth 2.0 |

---

## 🔐 How OAuth 2.0 Works Here

When a tool requiring authentication is called:

1. A **CSRF-safe state token** is generated via `secrets.token_urlsafe(16)`.
2. A **one-shot local HTTP server** starts on `localhost:9000` to receive the OAuth redirect.
3. The **bookshop consent page** opens in the user's default browser.
4. The user **logs in directly on the bookshop site** — credentials are never seen by the AI.
5. After approval, the auth code is **exchanged for a JWT Bearer token**.
6. The token is used to make authenticated API calls.

> ⏱️ The OAuth flow times out after **2 minutes** if the user does not complete login.

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- The bookshop backend running at `http://localhost:8080`
- [`uv`](https://github.com/astral-sh/uv) or `pip` for dependency management

### Installation

```bash
# Clone the repository
git clone https://github.com/psparmeet14/bookshop-mcp.git
cd bookshop-mcp

# Install dependencies
pip install httpx mcp
```

### Configuration

The server reads its configuration from environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `BOOKSHOP_MCP_CLIENT_SECRET` | `mcp-secret` | OAuth client secret for the MCP client |

Set it before running:

```bash
export BOOKSHOP_MCP_CLIENT_SECRET="your-secret-here"
```

### Running the Server

```bash
python server.py
```

The server communicates over **stdio**, which is the standard transport for MCP clients like Claude Desktop.

---

## ⚙️ Configuration Constants

Defined at the top of `server.py`:

```python
BOOKSHOP_BASE_URL = "http://localhost:8080"   # Bookshop backend URL
CALLBACK_PORT     = 9000                      # Local OAuth redirect listener port
CLIENT_ID         = "bookshop-mcp"            # OAuth client ID
```

---

## 🧪 Test Users

You can use these pre-configured users to test the authenticated tools:

| Username | Password |
|----------|----------|
| `alice`  | `alice123` |
| `bob`    | `bob123`   |

---

## 🔗 OAuth Endpoints (Bookshop Backend)

| Endpoint | Purpose |
|----------|---------|
| `GET /oauth/authorize` | Initiates the Authorization Code flow |
| `POST /oauth/token` | Exchanges auth code for a JWT access token |
| `GET /books` | Public book catalog |
| `GET /me/books` | User's personalized book list (requires Bearer token) |
| `GET /me/profile` | User's profile (requires Bearer token) |

---

## 📁 Project Structure

```
bookshop-mcp/
├── server.py       # MCP server with tools and OAuth flow
├── .gitignore
└── README.md
```

---

## 📄 License

This project is open-source. Feel free to use and modify it.
