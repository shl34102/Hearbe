import argparse
import asyncio
import json
import sys
from pathlib import Path

# Ensure MCP root is on sys.path when executed from this folder
MCP_ROOT = Path(__file__).resolve().parents[1]
if str(MCP_ROOT) not in sys.path:
    sys.path.insert(0, str(MCP_ROOT))

from browser.launcher import ChromeLauncher
from mcp.tools import BrowserTools


DEFAULT_CART_URL = "https://cart.coupang.com/cartView.pang"


async def run() -> int:
    parser = argparse.ArgumentParser(description="Check Coupang cart extraction via MCP BrowserTools.")
    parser.add_argument("--cdp-url", default="", help="Existing CDP WebSocket URL (optional).")
    parser.add_argument("--url", default=DEFAULT_CART_URL, help="URL to navigate before extraction.")
    parser.add_argument("--no-navigate", action="store_true", help="Skip navigation and use current page.")
    parser.add_argument("--wait-ms", type=int, default=1500, help="Wait time after navigation in ms.")
    parser.add_argument(
        "--close-browser",
        action="store_true",
        help="Close Chrome started by this script when done.",
    )
    args = parser.parse_args()

    tools = BrowserTools()
    launcher = None
    cdp_url = args.cdp_url.strip()

    if not cdp_url:
        launcher = ChromeLauncher()
        started = await launcher.start()
        if not started or not launcher.cdp_url:
            print("Failed to get CDP URL. Is Chrome running?", file=sys.stderr)
            return 1
        cdp_url = launcher.cdp_url

    connected = await tools.connect(cdp_url)
    if not connected:
        print("Failed to connect to browser via CDP.", file=sys.stderr)
        return 1

    if not args.no_navigate:
        nav = await tools.navigate_to_url(args.url)
        if not nav.get("success"):
            print(f"Navigation failed: {nav.get('error')}", file=sys.stderr)
            await tools.disconnect()
            return 1
        await asyncio.sleep(max(args.wait_ms, 0) / 1000.0)

    result = await tools.execute_tool("extract_cart", {})
    print(json.dumps(result, ensure_ascii=False, indent=2))

    await tools.disconnect()
    if launcher and launcher.is_running and args.close_browser:
        await launcher.stop()

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
