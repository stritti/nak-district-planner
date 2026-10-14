# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""API Middleware package."""

from app.adapters.api.middleware.csrf import CSRFMiddleware

__all__ = ["CSRFMiddleware"]
