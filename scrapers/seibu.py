import re
from datetime import timedelta, date
from playwright.sync_api import sync_playwright
from .base import Event

# カテゴリ2=グルメ絞り込みURL
TOPICS_URL = "https://www.sogo-seibu.jp/ikebukuro/topics/?cateid=2"
STORE = "西武池袋"
BASE_URL = "https://www.sogo-seibu.jp"

DATE_RANGE_RE = re.compile(
    r"(\d{4})[年/](\d{1,2})[月/](\d{1,2})日?[（(]?[^）)]*[）)]?\s*[～~〜-]\s*"
    r"(?:(\d{4})[年/])?(\d{1,2})[月/](\d{1,2})"
)
DATE_SINGLE_RE = re.compile(r"(\d{4})[年/](\d{1,2})[月/](\d{1,2})")


def _parse_range(text: str) -> tuple[str, str]:
    m = DATE_RANGE_RE.search(text)
    if m:
        y1, mo1, d1 = int(m.group(1)), int(m.group(2)), int(m.group(3))
        y2 = int(m.group(4)) if m.group(4) else y1
        mo2, d2 = int(m.group(5)), int(m.group(6))
        try:
            start = date(y1, mo1, d1)
            end = date(y2, mo2, d2) + timedelta(days=1)
            return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")
        except ValueError:
            pass
    m2 = DATE_SINGLE_RE.search(text)
    if m2:
        try:
            d = date(int(m2.group(1)), int(m2.group(2)), int(m2.group(3)))
            return d.strftime("%Y-%m-%d"), (d + timedelta(days=1)).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return "", ""


def scrape() -> list[Event]:
    events: list[Event] = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
            )
            ctx = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
                locale="ja-JP",
            )
            page = ctx.new_page()
            page.goto(TOPICS_URL, wait_until="domcontentloaded", timeout=45000)
            # Wixはレンダリングに時間がかかるため待機
            page.wait_for_timeout(6000)

            html = page.content()
            print(f"[seibu] page size: {len(html)} chars", flush=True)

            # Wixのブログ記事リンクをすべて取得
            anchors = page.query_selector_all("a[href*='/ikebukuro/topics/page/'], a[href*='/ikebukuro/topics/?']")
            print(f"[seibu] anchor candidates: {len(anchors)}", flush=True)

            seen_hrefs = set()
            for anchor in anchors:
                try:
                    href = anchor.get_attribute("href") or ""
                    if href in seen_hrefs:
                        continue
                    seen_hrefs.add(href)

                    full_url = href if href.startswith("http") else BASE_URL + href

                    # アンカーの内側テキストからタイトルを取得
                    title = anchor.inner_text().strip()
                    if not title or len(title) > 120:
                        continue

                    # 親要素からテキスト全体を取得して日付を探す
                    parent_text = page.evaluate(
                        """el => {
                            let p = el.closest('li') || el.closest('article') || el.closest('[role="listitem"]') || el.parentElement;
                            return p ? p.innerText : '';
                        }""",
                        anchor,
                    )

                    start, end = _parse_range(parent_text or title)
                    if not start:
                        continue

                    events.append(Event(
                        store=STORE,
                        title=title,
                        start=start,
                        end=end,
                        url=full_url,
                        floor="",
                        category="グルメ",
                    ))
                except Exception:
                    continue

            # アンカーで取れない場合は全テキストから日付ブロックを抽出
            if not events:
                print("[seibu] fallback: extracting from page text", flush=True)
                blocks = page.query_selector_all(
                    "[data-testid='post-list-item'], [data-hook='post-list-item'], "
                    ".post-list-item, article, li.blog-post"
                )
                for block in blocks:
                    try:
                        text = block.inner_text()
                        start, end = _parse_range(text)
                        if not start:
                            continue
                        # タイトルっぽい最初の行
                        lines = [l.strip() for l in text.splitlines() if l.strip()]
                        title = lines[0] if lines else text[:50]
                        link_el = block.query_selector("a[href]")
                        href = link_el.get_attribute("href") if link_el else ""
                        url = href if href.startswith("http") else BASE_URL + href if href else TOPICS_URL
                        events.append(Event(
                            store=STORE, title=title, start=start, end=end,
                            url=url, floor="", category="グルメ",
                        ))
                    except Exception:
                        continue

            browser.close()
    except Exception as e:
        print(f"[seibu] scrape error: {e}", flush=True)

    print(f"[seibu] raw events: {len(events)}", flush=True)
    return events
