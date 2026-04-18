import re
from datetime import timedelta, date
from playwright.sync_api import sync_playwright
from .base import Event

# 食品イベント専用ページ（通常のevent_calendarより軽い）
EVENT_URL = "https://www.mistore.jp/store/shinjuku/feature/foods/event_calendar.html"
STORE = "新宿伊勢丹"
BASE_HOST = "https://www.mistore.jp"

DATE_RANGE_RE = re.compile(
    r"(\d{4})[年/](\d{1,2})[月/](\d{1,2})日?[（(]?[^）)\n]*[）)]?\s*[～~〜]\s*"
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
            # networkidle は重いので load に変更、タイムアウトも延長
            page.goto(EVENT_URL, wait_until="load", timeout=60000)
            page.wait_for_timeout(5000)

            html = page.content()
            print(f"[isetan] page size: {len(html)} chars", flush=True)

            items = page.query_selector_all(
                ".eventCalendar__item, .event-list__item, .eventList__item, "
                "li.event-item, article.event, .schedule-item, tr.event-row"
            )
            print(f"[isetan] items found: {len(items)}", flush=True)

            for item in items:
                try:
                    title_el = item.query_selector("h2, h3, h4, .title, .eventName, .event-title")
                    if not title_el:
                        continue
                    title = title_el.inner_text().strip()

                    text = item.inner_text()
                    start, end = _parse_range(text)
                    if not start:
                        continue

                    link_el = item.query_selector("a[href]")
                    href = link_el.get_attribute("href") if link_el else ""
                    url = href if href.startswith("http") else BASE_HOST + href if href else EVENT_URL

                    events.append(Event(
                        store=STORE, title=title, start=start, end=end,
                        url=url, floor="", category="食品",
                    ))
                except Exception:
                    continue

            browser.close()
    except Exception as e:
        print(f"[isetan] scrape error: {e}", flush=True)

    return events
