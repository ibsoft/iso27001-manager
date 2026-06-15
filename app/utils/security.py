import bleach


ALLOWED_TAGS = [
    "p", "br", "strong", "em", "u", "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li", "a", "table", "thead", "tbody", "tr", "th", "td",
    "blockquote", "pre", "code", "hr",
]

ALLOWED_ATTRS = {
    "a": ["href", "title", "target"],
    "td": ["colspan", "rowspan"],
    "th": ["colspan", "rowspan"],
    "table": ["class"],
}


def sanitize_html(content):
    if content:
        return bleach.clean(content, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, strip=True)
    return content


def sanitize_text(content):
    if content:
        return bleach.clean(content, tags=[], strip=True)
    return content
