import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, date
from .base import Event

BASE_URL = "https://www.tobu-dept.jp"
STORE = "東武池袋"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
FAR_FUTURE = "99991231"


def _parse_yyyymmdd(s: str) -> date | None:
    try:
        return datetime.strptime(s[:8], "%Y%m%d").date()
    except Exception:
        return None


def _scrape_month_url(url: str) -> list[Event]:
    events = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.encoding = "utf-8"
        soup = BeautifulSoup(resp.text, "html.parser")

        for li in soup.select("#sec_cnts li[data-open]"):
            data_open = li.get("data-open", "")
            data_close = li.get("data-close", "")

            start_d = _parse_yyyymmdd(data_open)
            if not start_d:
                continue

            # 9999xxxx は期限なし（常設ページ）→ 60日間で表示
            if data_close.startswith("9999"):
                end_d = start_d + timedelta(days=60)
            else:
                end_d = _parse_yyyymmdd(data_close)
                if not end_d:
                    end_d = start_d

            # FullCalendar の end は exclusive (+1日)
            end_d = end_d + timedelta(days=1)

            title_el = li.select_one("div.sttl h3")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)

            # フロア: sttl 内の txt01 span（h3 の前）
            floor_el = li.select_one("div.sttl p.txt01 span")
            floor = floor_el.get_text(strip=True) if floor_el else ""

            link_el = li.select_one("div.btn a")
            url_path = link_el["href"] if link_el else ""
            full_url = BASE_URL + url_path if url_path.startswith("/") else url_path or url

            events.append(Event(
                store=STORE,
                title=title,
                start=start_d.strftime("%Y-%m-%d"),
                end=end_d.strftime("%Y-%m-%d"),
                url=full_url,
                floor=floor,
                category="",
            ))

        time.sleep(2)
    except Exception as e:
        print(f"[tobu] error {url}: {e}")
    return events


def scrape() -> list[Event]:
    today = date.today()
    urls = [f"{BASE_URL}/ikebukuro/event/"]
    # 今月 + 翌2ヶ月分も取得
    for delta in range(1, 3):
        m = today.month + delta
        y = today.year + (m - 1) // 12
        m = ((m - 1) % 12) + 1
        urls.append(f"{BASE_URL}/ikebukuro/event/1/{y}/{m}")

    seen = set()
    all_events = []
    for u in urls:
        for ev in _scrape_month_url(u):
            if ev.id not in seen:
                seen.add(ev.id)
                all_events.append(ev)

    return all_events
