import re
import time
import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateparser
from datetime import timedelta
from .base import Event

BASE_URL = "https://www.sogo-seibu.jp"
TOPICS_URL = f"{BASE_URL}/ikebukuro/topics/"
STORE = "西武池袋"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

FOOD_CATEGORY_KEYWORDS = ["グルメ", "スイーツ", "食", "フード", "デパ地下", "gourmet", "弁当"]


def _parse_date_range(text: str) -> tuple[str, str]:
    text = text.strip().replace("～", "~").replace("\u301c", "~")
    parts = text.split("~")
    try:
        start_dt = dateparser.parse(parts[0].strip(), fuzzy=True)
        if len(parts) > 1:
            end_raw = parts[1].strip()
            if re.match(r"^\d{1,2}[/月]", end_raw):
                end_raw = f"{start_dt.year}年{end_raw}" if "月" in end_raw else f"{start_dt.year}/{end_raw}"
            end_dt = dateparser.parse(end_raw, fuzzy=True)
        else:
            end_dt = start_dt
        return start_dt.strftime("%Y-%m-%d"), (end_dt + timedelta(days=1)).strftime("%Y-%m-%d")
    except Exception:
        return "", ""


def _get_page(page: int) -> BeautifulSoup | None:
    url = TOPICS_URL if page == 1 else f"{TOPICS_URL}?page={page}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.encoding = resp.apparent_encoding
        time.sleep(2)
        return BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        print(f"[seibu] page {page} error: {e}")
        return None


def scrape() -> list[Event]:
    events: list[Event] = []
    page = 1
    while page <= 5:  # 最大5ページまで
        soup = _get_page(page)
        if soup is None:
            break

        items = soup.select(".topics-list__item, .topicsList__item, article.topics")
        if not items:
            break

        for item in items:
            title_el = item.select_one("h3, h2, .topics-title, .title")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)

            # カテゴリタグ取得
            category_els = item.select(".category, .tag, .label")
            category = ", ".join(el.get_text(strip=True) for el in category_els)

            period_el = item.select_one(".period, .date, time")
            period_text = period_el.get_text(strip=True) if period_el else ""

            floor_el = item.select_one(".floor, .place")
            floor = floor_el.get_text(strip=True) if floor_el else ""

            link_el = item.select_one("a[href]")
            url = BASE_URL + link_el["href"] if link_el and link_el["href"].startswith("/") else (link_el["href"] if link_el else TOPICS_URL)

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
                category=category,
            ))

        # 次ページがなければ終了
        next_btn = soup.select_one("a.next, .pagination .next, [rel='next']")
        if not next_btn:
            break
        page += 1

    return events
