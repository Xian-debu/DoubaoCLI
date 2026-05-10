"""Cookie management — extract from browser, load from file, validate."""

import time
from pathlib import Path
from .config import AUTH_INDICATORS, DEFAULT_COOKIE_PATH, AuthStatus, AuthError


def parse_netscape_cookies(filepath: str | Path, domain_filter: str | None = None) -> list[dict]:
    """Parse Netscape-format cookie file (7 tab-separated fields)."""
    cookies = []
    path = Path(filepath).expanduser()
    if not path.exists():
        return cookies
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 7:
                continue
            domain, name, value = parts[0], parts[5], parts[6]
            if domain_filter and domain_filter not in domain:
                continue
            cookies.append({"name": name, "value": value, "domain": domain})
    return cookies


def cookies_to_header(cookies: list[dict]) -> str:
    return "; ".join(f"{c['name']}={c['value']}" for c in cookies)


class AuthManager:
    """Extracts cookies from a CDP-connected browser and validates login state.

    Usage:
        cdp = CDPManager(); cdp.connect()
        auth = AuthManager(cdp)
        if auth.is_logged_in().is_logged_in:
            auth.save()  # save to ~/.doubaocli/cookies.txt
    """

    def __init__(self, cdp=None, cookie_path=DEFAULT_COOKIE_PATH):
        self.cdp = cdp
        self.cookie_path = Path(cookie_path)

    def extract(self) -> list[dict]:
        if not self.cdp or not self.cdp.connected:
            raise AuthError("CDP not connected")
        cookies = []
        for ctx in self.cdp._browser.contexts:
            cookies.extend(ctx.cookies())
        return [c for c in cookies if any(
            d in c.get("domain", "") for d in ["doubao.com", "bytedance.com"]
        )]

    def validate(self, cookies=None) -> AuthStatus:
        if cookies is None:
            try: cookies = self.extract()
            except AuthError: return AuthStatus(is_logged_in=False, cookie_count=0)
        auth_key = None
        for c in cookies:
            if c.get("name") in AUTH_INDICATORS and c.get("value", "").strip():
                auth_key = c["name"]; break
        return AuthStatus(is_logged_in=auth_key is not None,
                          auth_key=auth_key, cookie_count=len(cookies))

    def save(self, cookies=None, path=None) -> int:
        if cookies is None: cookies = self.extract()
        target = Path(path) if path else self.cookie_path
        target.parent.mkdir(parents=True, exist_ok=True)
        lines = ["# Netscape HTTP Cookie File", f"# {time.ctime()}", ""]
        for c in cookies:
            domain = c.get("domain", ".doubao.com")
            flag = "TRUE" if domain.startswith(".") else "FALSE"
            lines.append(f"{domain}\t{flag}\t{c.get('path','/')}\t"
                         f"{'TRUE' if c.get('secure') else 'FALSE'}\t"
                         f"{int(c.get('expires',-1))}\t{c['name']}\t{c['value']}")
        target.write_text("\n".join(lines) + "\n")
        return len(cookies)

    def load(self, path=None) -> list[dict]:
        target = Path(path) if path else self.cookie_path
        return parse_netscape_cookies(target, domain_filter="doubao.com")

    def is_logged_in(self) -> AuthStatus:
        try:
            cookies = self.extract()
            return self.validate(cookies)
        except AuthError:
            return self.validate(self.load())

    def refresh(self) -> bool:
        try: self.save(); return True
        except AuthError: return False

    def get_cookie_header(self, cookies=None) -> str:
        if cookies is None: cookies = self.load()
        return cookies_to_header(cookies)
