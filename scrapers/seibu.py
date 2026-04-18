import re
from datetime import timedelta, date
from dateutil import parser as dateparser
from playwright.sync_api import sync_playwright
from .base import Event

TOPICS_URL = "https://www.sogo-seibu.jp/ikebukuro/topics/"
STORE = "西武池袋"
BASE_URL = "https://www.sogo-seibu.jp"

# 西武はWix製サイトのためPlaywright必須
DATE_RANGE_RE = re.compile(
    r"(\d{4})[年/](\d{1,2})[月/](\d{1,2})日?[（(][^）)]*[）)]?\s*[～~〜]\s*"
    r"(?:(\d{4})[年/])?(\d{1,2})[月/](\d{1,2})"
)
DATE_SINGLE_RE = re.compile(r"(\d{4})[年/](\d{1,2})[月/](\d{1,2})")

FOOD_CATEGORIES = ["グルメ", "スイーツ", "食", "フード", "デパ地下", "gourmet", "弁当", "お弁当"]


def _parse_range(text: str) -> tuple[str, str]:
    text = text.strip()
    m = DATE_RANGE_RE.search(text)
    if m:
        y1, mo1, d1 = int(m.group(1)), int(m.group(2)), int(m.group(3))
        y2 = int(m.group(4)) if m.group(4) else y1
        mo2, d2 = int(m.group(5)), int(m.group(6))
        start = date(y1, mo1, d1)
        end = date(y2, mo2, d2) + timedelta(days=1)
        return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")
    m2 = DATE_SINGLE_RE.search(text)
    if m2:
        d = date(int(m2.group(1)), int(m2.group(2)), int(m2.group(3)))
        return d.strftime("%Y-%m-%d"), (d + timedelta(days=1)).strftime("%Y-%m-%d")
    return "", ""


def scrape() -> list[Event]:
    events: list[Event] = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
                locale="ja-JP",
            )
            page = ctx.new_page()
            page.goto(TOPICS_URL, wait_until="networkidle", timeout=40000)
            page.wait_for_timeout(4000)

            # Wixの汎用的なリストアイテムを探す
            # data-testid や role="listitem" など Wix 特有の属性を試みる
            items = page.query_selector_all("[data-testid='richTextElement'], [role='listitem'], .blog-post-item, article")

            if not items:
                # フォールバック: テキストから日付を含む塊を探す
                all_text_blocks = page.query_selector_all("a[href*='/ikebukuro/topics/']")
                for anchor in all_text_blocks:
                    try:
                        title = anchor.inner_text().strip()
                        if not title or len(title) > 100:
                            continue
                        href = anchor.get_attribute("href") or ""
                        url = href if href.startswith("http") else BASE_URL + href

                        # 親要素からテキスト全体を取得して日付を探す
                        parent = anchor.evaluate_handle("el => el.closest('li') || el.closest('article') || el.parentElement")
                        if parent:
                            parent_text = page.evaluate("el => el ? el.innerText : ''", parent)
                            start, end = _parse_range(parent_text)
                            if not start:
                                continue

                            # カテゴリ判定
                            category = ""
                            for kw in FOOD_CATEGORIES:
                                if kw in parent_text:
                                    category = kw
                                    break

                            events.append(Event(
                                store=STORE,
                                title=title,
                                start=start,
                                end=end,
                                url=url,
                                floor="",
                                category=category,
                            ))
                    except Exception:
                        continue
            else:
                for item in items:
                    try:
                        title_el = item.query_selector("h2, h3, h4, [data-hook='post-title']")
                        if not title_el:
                            continue
                        title = title_el.inner_text().strip()

                        inner_text = item.inner_text()
                        start, end = _parse_range(inner_text)
                        if not start:
                            continue

                        category_text = ""
                        cat_els = item.query_selector_all("[data-hook='post-category'], .category")
                        if cat_els:
                            category_text = ", ".join(el.inner_text().strip() for el in cat_els)

                        link_el = item.query_selector("a[href]")
                        href = link_el.get_attribute("href") if link_el else ""
                        url = href if href.startswith("http") else BASE_URL + (href or "")

                        events.append(Event(
                            store=STORE,
                            title=title,
                            start=start,
                            end=end,
                            url=url,
                            floor="",
                            category=category_text,
                        ))
                    except Exception:
                        continue

            browser.close()
    except Exception as e:
        print(f"[seibu] scrape error: {e}")

    return events
