"""Backend entrypoint — select mode via VIONA_MODE env var."""
from __future__ import annotations

import os

mode = os.getenv("VIONA_MODE", "api")

if mode == "agent":
    from app.agents.worker import main
elif mode == "api":
    from app.api.app import main  # type: ignore[assignment]
else:
    raise SystemExit(f"Unknown VIONA_MODE={mode!r}. Use 'api' or 'agent'.")

if __name__ == "__main__":
    main()
