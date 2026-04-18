"""
departevent.net から 高島屋・伊勢丹・三越 の催事データを取得する。
公式サイトが GitHub Actions IP をブロックするため代替ソースとして使用。
"""
import re
import time
import requests
from bs4 import BeautifulSoup
from datetime import date, timedelta
from .base import Event

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

BUSSAN_URL = "https://www.departevent.net/bussan.html"
DEPACHIKA_URL = "https://www.departevent.net/msstoreedpachika.html"

# departevent.net の見出しテキスト → 我々の店舗名マッピング
STORE_MAP = {
    "新宿タカシマヤ": "新宿高島屋",
    "新宿高島屋": "新宿高島屋",
    "日本橋三越本店": "日本橋三越",
    "伊勢丹新宿店": "新宿伊勢丹",
    "新宿伊勢丹": "新宿伊勢丹",
}

# 催事サイトの公式URL（代替ソース使用時のリンク先）
STORE_URLS = {
    "新宿高島屋": "https://www.takashimaya.co.jp/shinjuku/topics/event.html",
    "新宿伊勢丹": "https://www.mistore.jp/store/shinjuku/event_calendar.html",
    "日本橋三越": "https://www.mistore.jp/store/nihombashi/event_calendar.html",
}

DATE_RANGE_RE = re.compile(
    r"(\d{1,2})/(\d{1,2})\s*[〜～~]\s*(?:(\d{1,2})/)?(\d{1,2})"
)


def _parse_date(text: str, base_year: int) -> tuple[str, str]:
    """'4/16〜29' や '4/22〜5/6' や '3/26〜4/7' を (start, end+1) に変換"""
    text = text.strip()
    m = DATE_RANGE_RE.search(text)
    if not m:
        return "", ""
    try:
        sm, sd = int(m.group(1)), int(m.group(2))
        em = int(m.group(3)) if m.group(3) else sm
        ed = int(m.group(4))
        start = date(base_year, sm, sd)
        end = date(base_year, em, ed) + timedelta(days=1)
        return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")
    except ValueError:
        return "", ""


def _scrape_page(url: str, target_stores: set[str]) -> list[Event]:
    """ページ内のテーブルをパースしてイベントリストを返す"""
    events: list[Event] = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.encoding = resp.apparent_encoding
        soup = BeautifulSoup(resp.text, "html.parser")

        # ページ上部の年を抽出（例: "2026年4月東京のデパート..."）
        h1 = soup.find("h1")
        year_match = re.search(r"(\d{4})年", h1.get_text() if h1 else "")
        base_year = int(year_match.group(1)) if year_match else date.today().year

        current_store: str | None = None

        for tag in soup.find_all(["h2", "h3", "table"]):
            if tag.name in ("h2", "h3"):
                text = tag.get_text(strip=True)
                for key, store_name in STORE_MAP.items():
                    if key in text and store_name in target_stores:
                        current_store = store_name
                        break
                else:
                    # マッピングにない見出しが来たらリセット
                    if current_store and not any(k in text for k in STORE_MAP):
                        current_store = None

            elif tag.name == "table" and current_store:
                for row in tag.find_all("tr"):
                    cells = row.find_all(["td", "th"])
                    if len(cells) < 2:
                        continue
                    date_text = cells[0].get_text(strip=True)
                    event_text = cells[1].get_text(strip=True).lstrip("◎").strip()
                    if not event_text:
                        continue

                    start, end = _parse_date(date_text, base_year)
                    if not start:
                        continue

                    # イベント名が長い場合は最初のアイテム名だけ使う
                    # （伊勢丹のフードコレクションは複数出店者が入っている）
                    title = event_text.split("\n")[0].split("　")[0][:80]

                    events.append(Event(
                        store=current_store,
                        title=title,
                        start=start,
                        end=end,
                        url=STORE_URLS.get(current_store, ""),
                        floor="",
                        category="食品",
                    ))

        time.sleep(2)
    except Exception as e:
        print(f"[departevent] error {url}: {e}", flush=True)

    return events


def scrape_takashimaya() -> list[Event]:
    return _scrape_page(BUSSAN_URL, {"新宿高島屋"})


def scrape_isetan() -> list[Event]:
    # depachika は個別ブランド単位で件数が多すぎるため bussan のみ使用
    return _scrape_page(BUSSAN_URL, {"新宿伊勢丹"})


def scrape_mitsukoshi() -> list[Event]:
    return _scrape_page(BUSSAN_URL, {"日本橋三越"})
