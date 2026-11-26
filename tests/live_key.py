#
# Copyright (c) 2026, Jayanng
#
# SPDX-License-Identifier: BSD 2-Clause License
#

"""Live-test key resolution.

The live tests need a real GMI Cloud key, and the key must never be
written into code, files, or logs. Resolution order:

1. ``GMI_CLOUD_API_KEY`` from the environment, when the user sets it.
2. The registered ``custom.gmi-cloud`` credential, fetched at runtime as
   a short-lived placeholder that the local egress replaces with the real
   key only for approved GMI hosts. The placeholder itself is not a usable
   key outside this machine.
"""

import os
import sys

CREDENTIAL_HELPER_DIR = "/opt/muse/skills/custom-connector-setup/bin"


def resolve_live_api_key() -> str | None:
    """Return a live GMI Cloud API key, or None when none is available."""
    env_key = os.environ.get("GMI_CLOUD_API_KEY")
    if env_key:
        return env_key
    sys.path.insert(0, CREDENTIAL_HELPER_DIR)
    try:
        from dynamic_credentials import dynamic_credential_entry

        entry = dynamic_credential_entry("custom.gmi-cloud", "access_token")
        # "surrogate" is the credential service's own field name for the placeholder.
        return str(entry["surrogate"])
    except Exception:
        return None
