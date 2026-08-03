"""Commerce domain: catalog, cart, checkout, orders, fulfilment, returns.

Layering is deliberate and one-directional:

    api -> services -> {inventory, pricing, payments} -> models -> db

``services`` orchestrates and owns transactions. ``inventory``, ``pricing`` and
``payments`` hold isolated rules and never import ``api`` or ``services``, which keeps
each of them unit-testable without an HTTP client or a running application.
"""

from __future__ import annotations

__all__ = ["api", "db", "inventory", "models", "payments", "pricing", "security", "services"]
