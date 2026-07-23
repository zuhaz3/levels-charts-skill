# Company logos (optional)

Some builders — chiefly `company_strip` (pay-ranges-by-company) — use a company's
**brand logo as the row label** instead of text. Logos are an *optional* nicety:
without them the skill still renders everything, it just falls back to text labels.

Logos are **not bundled** in this repo (they're third-party trademarks). Instead the
engine fetches them on demand from [logo.dev](https://logo.dev) and caches them under
`assets/company_logos/` (gitignored). You bring your own free key.

## Setup (one time)
1. Get a free publishable token at **https://logo.dev** (starts with `pk_`).
2. Export it in your shell (add to `~/.zshrc` / `~/.bashrc` to persist):
   ```bash
   export LOGO_DEV_TOKEN="pk_your_token_here"
   ```
3. Some logo.dev keys are **domain-allowlisted** — they only work when the request
   carries a matching `Referer`. If yours is, also set:
   ```bash
   export LOGO_DEV_REFERER="https://yourdomain.com"
   ```
   (Leave it unset if your key isn't domain-restricted.)

Without `LOGO_DEV_TOKEN`, `company_logo()` returns `None` (and prints a one-time
hint); pass a plain string label instead and charts render fine.

## Fetching a logo
`company_logo(domain, *, size=256, greyscale=False, refresh=False)` returns an RGBA
`ndarray` (or `None`), fetching + caching on first call, then reading the cache after:
```python
from levels_charts import company_logo, rgb_str, company_strip
amzn = company_logo("amazon.com")            # RGBA ndarray, cached to assets/company_logos/
amzn_grey = company_logo("amazon.com", greyscale=True)   # muted / mono variant
```
- **`domain`**, not company name — `"stripe.com"`, `"amazon.com"`, `"block.xyz"`.
- **`greyscale=True`** for a muted mark (good on the cream background when color would clash).
- **`refresh=True`** re-fetches even if cached (use if a brand updated its logo).

## Practice — how we use them
- **As row labels in `company_strip`.** Each row is `(label, points_$K, color[, name])`
  where `label` is the logo `ndarray` (or a string). Pass a 4th `name` string to print the
  company name *under* the logo when the mark alone isn't recognizable:
  ```python
  rows = [
      (company_logo("netflix.com"), netflix_points, "#E50914"),
      (company_logo("airbnb.com"),  airbnb_points,  "#FF5A5F", "Airbnb"),
  ]
  company_strip(ax, rows, ...)     # portrait format suits 6+ rows
  ```
- **Color from the brand, not guesswork.** If you have a Levels `company.color`
  (an `[r,g,b]` array), convert it with `rgb_str(company.color)` for the row's dot/box color;
  or derive the dominant color straight from the logo with `logo_color(company_logo(domain))`.
- **Sizing is automatic** — the builders scale the logo into the left gutter (`STRIP_LEFT`),
  so don't pre-resize. Use `size=256` (default) for crisp marks at chart resolution.
- **Fallbacks read fine.** When a logo is missing/`None`, use the company name string as the
  label — the layout is designed to look clean either way, so a mixed logo/text set is OK.
- **Don't distort or recolor** a fetched brand logo; only the greyscale variant is a sanctioned
  restyle. Logos are used purely as data labels, and remain trademarks of their owners.
