"""Ізольований процес реальної MultiServerMCPClient stdio-демонстрації."""

from __future__ import annotations

import asyncio
import json

from hw3_smm.mcp_integration import integration_summary


if __name__ == "__main__":
    print(json.dumps(asyncio.run(integration_summary()), ensure_ascii=False))
