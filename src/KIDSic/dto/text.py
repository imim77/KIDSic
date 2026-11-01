"""Shared Croatian text normalization for search criteria and stored keys."""
import unicodedata


def normalize(value: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFD', value.lower()) if not unicodedata.combining(c)).replace('đ', 'd').strip()
