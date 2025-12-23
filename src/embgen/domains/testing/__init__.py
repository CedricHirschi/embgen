"""Testing domain for embgen test suite.

This domain provides comprehensive templates for testing all embgen features:
- Single-file templates (.txt, .json)
- Multi-file templates with different extensions (.h/.c pair)
- Multi-file templates with same extension and suffix (.dat.1, .dat.2, .dat.3)
- Post-generate hook testing
"""

from .generator import TestingGenerator

# This is all that's needed for auto-discovery
generator = TestingGenerator()
