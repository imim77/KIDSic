"""Compatibility entry point for scripts using the original normalization function."""
from KIDSic.services.concrete.parsers import default_parsers
from KIDSic.services.concrete.source_normalizer import SourceRecordNormalizer


def normalize_records(records, parser):
    return SourceRecordNormalizer(default_parsers()).normalize(records, parser)
