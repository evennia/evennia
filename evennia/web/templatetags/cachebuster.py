from django import template
from django.conf import settings
from django.contrib.staticfiles import finders

register = template.Library()

@register.filter
def cachebust(value, digest_size=5):
    filepath = finders.find(value.removeprefix(settings.STATIC_URL))
    if not filepath:
        return value
    
    with open(filepath, "rb") as f:
        import hashlib
        filehash = hashlib.shake_256(f.read()).hexdigest(digest_size)
        return f"{value}?{filehash}"
