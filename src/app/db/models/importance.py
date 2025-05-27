import enum


class Importance(enum.Enum):
    """Importance levels for todo items."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
