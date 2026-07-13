from __future__ import unicode_literals

import contextvars

# Size of the most recent Xero API response on this execution context, so callers
# can attribute egress per request. `content_length` is the Content-Length header
# (bytes transferred over the wire, i.e. the compressed size when compressed);
# `body_bytes` is the decoded body length.
last_response_size = contextvars.ContextVar("xero_last_response_size", default=None)


def record_response_size(response):
    try:
        content_length = response.headers.get("Content-Length")
        last_response_size.set(
            {
                "content_length": (
                    int(content_length) if content_length is not None else None
                ),
                "body_bytes": len(response.content),
            }
        )
    except Exception:
        last_response_size.set(None)
