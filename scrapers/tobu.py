import re
import time
import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateparser
from .base import Event

BASE_URL = "https://www.tobu-dept.jp"
EVENT_URL = f"{BASE_URL}/ikebukuro/event/"
STORE = "東武池袋"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def _parse_date_range(text: str) -> tuple[str, str]:
    """'2026年4月22日（水）～5月6日（水）' → ('2026-04-22', '2026-05-07')"""
    text = text.strip().replace("\u301c", "~").replace("～", "~")
    parts = text.split("~")
    try:
        start_dt = dateparser.parse(parts[0].strip(), fuzzy=True, yearfirst=False)
        if len(parts) > 1:
            end_raw = parts[1].strip()
            # 終了日は年が省略されている場合がある ("5月6日") → 開始年月を補完
            if re.match(r"^\d{1,2}月", end_raw):
                end_raw = f"{start_dt.year}年{end_raw}"
            end_dt = dateparser.parse(end_raw, fuzzy=True, yearfirst=False)
        else:
            end_dt = start_dt
        # FullCalendar の end は exclusive なので +1日
        from datetime import timedelta
        start_str = start_dt.strftime("%Y-%m-%d")
        end_str = (end_dt + timedelta(days=1)).strftime("%Y-%m-%d")
        return start_str, end_str
    except Exception:
        return "", ""


def scrape() -> list[Event]:
    events: list[Event] = []
    try:
        resp = requests.get(EVENT_URL, headers=HEADERS, timeout=20)
        resp.encoding = resp.apparent_encoding
        soup = BeautifulSoup(resp.text, "html.parser")

        for item in soup.select(".eventList__item, .event-item, article.event"):
            title_el = item.select_one("h3, h2, .event-title, .title")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)

            period_el = item.select_one(".period, .date, .event-date, time")
            period_text = period_el.get_text(strip=True) if period_el else ""

            floor_el = item.select_one(".floor, .place, .location")
            floor = floor_el.get_text(strip=True) if floor_el else ""

            link_el = item.select_one("a[href]")
            url = BASE_URL + link_el["href"] if link_el and link_el["href"].startswith("/") else (link_el["href"] if link_el else EVENT_URL)

            start, end = _parse_date_range(period_text)
            if not start:
                continue

            events.append(Event(
                store=STORE,
                title=title,
                start=start,
                end=end,
                url=url,
                floor=floor,
                category="",
            ))

        time.sleep(2)
    except Exception as e:
        print(f"[tobu] scrape error: {e}")

    return events
