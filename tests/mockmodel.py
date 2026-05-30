"""Back-compat shim: the MockModel now ships in the package as `hostaagent.testing`.

Existing tests do `from mockmodel import MockModel`; keep that working by re-exporting.
"""
from hostaagent.testing import MockModel  # noqa: F401  (re-export for tests)
