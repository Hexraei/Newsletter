"""Shared async database URL normalization for runtime and migrations."""
import ssl
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def async_database_config(url: str):
    parts = urlsplit(url)
    scheme = parts.scheme
    if scheme in {"postgres", "postgresql"}:
        scheme = "postgresql+asyncpg"
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    connect_args = {}
    ssl_mode = query.pop("sslmode", query.pop("ssl", None))
    query.pop("channel_binding", None)
    if ssl_mode in {"require", "verify-ca", "verify-full"}:
        # Require encrypted transport and validate the peer certificate.
        connect_args["ssl"] = ssl.create_default_context()
    elif ssl_mode == "disable":
        connect_args["ssl"] = False
    normalized = urlunsplit((scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))
    return normalized, connect_args
