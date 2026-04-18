import re
import time
from datetime import timedelta
from dateutil import parser as dateparser
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
from .base import Event

EVENT_URL = "https://www.takashimaya.co.jp/shinjuku/topics/event.html"
STORE = "新宿高島屋"


def _parse_date_range(text: str) -> tuple[str, str]:
    text = text.strip().replace("～", "~").replace("\u301c", "~")
    parts = text.split("~")
    try:
        start_dt = dateparser.parse(parts[0].strip(), fuzzy=True)
        if len(parts) > 1:
            end_raw = parts[1].strip()
            if re.match(r"^\d{1,2}月", end_raw):
                end_raw = f"{start_dt.year}年{end_raw}"
            end_dt = dateparser.parse(end_raw, fuzzy=True)
        else:
            end_dt = start_dt
        return start_dt.strftime("%Y-%m-%d"), (end_dt + timedelta(days=1)).strftime("%Y-%m-%d")
    except Exception:
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
            page.goto(EVENT_URL, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)

            items = page.query_selector_all("li.topicsList__item, article.event-item, .topics-list li")
            for item in items:
                title_el = item.query_selector("h3, h2, .title, .topicsList__title")
                if not title_el:
                    continue
                title = title_el.inner_text().strip()

                period_el = item.query_selector(".period, .date, time, .topicsList__date")
                period_text = period_el.inner_text().strip() if period_el else ""

                floor_el = item.query_selector(".floor, .place, .location")
                floor = floor_el.inner_text().strip() if floor_el else ""

                link_el = item.query_selector("a[href]")
                url = link_el.get_attribute("href") if link_el else EVENT_URL
                if url and url.startswith("/"):
                    url = "https://www.takashimaya.co.jp" + url

                start, end = _parse_date_range(period_text)
                if not start:
                    continue

                events.append(Event(
                    store=STORE,
                    title=title,
                    start=start,
                    end=end,
                    url=url or EVENT_URL,
                    floor=floor,
                    category="",
                ))

            browser.close()
    except Exception as e:
        print(f"[takashimaya] scrape error: {e}")

    return events
