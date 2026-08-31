"""Yu Memory Kernel: Event (append-only) + Memory persistence + Provenance Grounding."""

from . import provenance
from .correction import CorrectionResult, MemoryCorrectionService, is_correction
from .guard import AttributionVerdict, MemoryAttributionGuard, detect_historical_claims, has_verified_support
from .models import Event, Memory
from .router import (
    MEMORY_ARCHIVE,
    MEMORY_CORRECT,
    MEMORY_CREATE,
    MEMORY_READ,
    MEMORY_SEARCH,
    MEMORY_UPDATE,
    MemoryIntent,
    detect_memory_intent,
)
from .service import MemoryResult, MemoryService, ReferenceResolution
from .store import MemoryStore
from .validator import MemoryWriteError, MemoryWriteValidator, WriteDecision

__all__ = [
    "Event",
    "Memory",
    "MemoryStore",
    "MemoryWriteValidator",
    "MemoryWriteError",
    "WriteDecision",
    "MemoryAttributionGuard",
    "AttributionVerdict",
    "detect_historical_claims",
    "MemoryCorrectionService",
    "CorrectionResult",
    "is_correction",
    "has_verified_support",
    "MemoryService",
    "MemoryResult",
    "ReferenceResolution",
    "detect_memory_intent",
    "MemoryIntent",
    "MEMORY_CREATE",
    "MEMORY_READ",
    "MEMORY_SEARCH",
    "MEMORY_UPDATE",
    "MEMORY_CORRECT",
    "MEMORY_ARCHIVE",
    "provenance",
]