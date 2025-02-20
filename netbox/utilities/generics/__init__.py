__all__ = [
    "GenericArrayForeignKey",
    "GenericPrefetch",
    "GenericForeignKey",
]

from .genprefetch import GenericPrefetch
from .field import GenericArrayForeignKey
from .fk import GenericForeignKey
