# Security

Known security considerations and hardening steps for production deployment.

## Open Items

### API Authentication

The API currently has no authentication. Anyone who can reach port 8000 can submit HTML for extraction. This is fine for localhost development but must be addressed before public deployment.

Recommended approach: add a simple API key via environment variable.

```python
# In api.py — middleware or dependency that checks X-API-Key header
API_KEY = os.environ.get("BRIGHTSPACE_API_KEY")

async def verify_api_key(request: Request):
    if API_KEY and request.headers.get("X-API-Key") != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
```

The extension would store the API key alongside the base URL in `chrome.storage.local` and include it in every request.

For multi-user deployment, consider OAuth2 or a reverse proxy with authentication (e.g. Caddy with basicauth, or Cloudflare Access).

### Docker Non-Root User

The Dockerfile currently runs the application as root inside the container. This increases the blast radius if a container escape vulnerability is exploited.

Fix by adding a non-root user:

```dockerfile
RUN useradd --create-home appuser
USER appuser
```

Add this after the `RUN uv sync` step and before `EXPOSE`. Ensure the app directory is readable by the new user.

### HTTPS

The API serves plain HTTP. For production, terminate TLS at a reverse proxy:

- Caddy (automatic HTTPS via Let's Encrypt)
- nginx with certbot
- Cloudflare Tunnel

Never expose the API directly on port 8000 over the internet without TLS.

## Mitigated

### XSS in Extension Popup

All dynamic content rendered in the popup is escaped via `escapeHtml()` before insertion into `innerHTML`. This prevents injection from malicious Brightspace field values (student names, group names, etc.).

### Request Body Size Limit

The API enforces a 10 MB body size limit on all endpoints. Brightspace pages are typically 1-3 MB. Requests exceeding the limit receive HTTP 413.

### CORS Restriction

The API only allows CORS requests from `chrome-extension://` and `moz-extension://` origins. Browser requests from arbitrary websites are rejected.

### Error Information Disclosure

API error responses return generic messages via `{"detail": "..."}`. Stack traces and internal paths are never exposed to clients — they are logged server-side only.
