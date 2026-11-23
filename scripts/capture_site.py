"""Capture a REAL screenshot of a tool's website for <ScreenFrame src=...>.

    python3 tools/capture_site.py https://claude.ai --name claude-home
    python3 tools/capture_site.py https://cursor.com --name cursor --mobile --height 2600

Uses headless Chrome/Chromium already on the machine (no extra installs). Output:
public/img/screens/<name>.png. Always prefer real screenshots / screen recordings over mock UIs
when introducing a product — they are what makes a tool review credible.
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def find_chrome() -> str:
    for c in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome", "msedge"):
        p = shutil.which(c)
        if p:
            return p
    mac = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    if mac.exists():
        return str(mac)
    sys.exit("[CAPTURE] Chrome/Chromium not found. Install it or place a screenshot in user_inputs/assets/ready/.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url")
    ap.add_argument("--name", required=True)
    ap.add_argument("--mobile", action="store_true", help="430px-wide mobile layout")
    ap.add_argument("--width", type=int, default=None)
    ap.add_argument("--height", type=int, default=1800)
    ap.add_argument("--wait", type=int, default=4000, help="ms to let the page render")
    args = ap.parse_args()
    width = args.width or (430 if args.mobile else 1280)
    out = Path("public/img/screens") / f"{args.name}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        find_chrome(), "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
        f"--window-size={width},{args.height}", f"--virtual-time-budget={args.wait}",
        "--force-device-scale-factor=2", f"--screenshot={out.resolve()}", args.url,
    ]
    if args.mobile:
        cmd.insert(1, "--user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"[CAPTURE] {args.url} -> {out}  (check it: cookie banners / login walls must not be visible)")


if __name__ == "__main__":
    main()
