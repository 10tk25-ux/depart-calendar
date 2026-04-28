"""
bussanten.info から 伊勢丹新宿・日本橋三越・新宿高島屋 の催事を取得する。

mistore.jp / takashimaya.co.jp が GitHub Actions IP をブロックするため、
この代替ソースを使用する。各催事の記事ページに店舗・フロア・日程が記載されている。
"""
import re
import time
import requests
from bs4 import BeautifulSoup
from datetime import date, timedelta
from .base import Event

BASE_URL = "https://www.bussanten.info"
TOP_URL  = "https://www.bussanten.info/"
HEADERS  = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

STORE_MAP = {
    "伊勢丹新宿店": "新宿伊勢丹",
    "伊勢丹新宿":   "新宿伊勢丹",
    "新宿伊勢丹":   "新宿伊勢丹",
    "日本橋三越本店": "日本橋三越",
    "日本橋三越":   "日本橋三越",
    "新宿高島屋":   "新宿高島屋",
    "新宿タカシマヤ": "新宿高島屋",
}
TARGET_STORES = set(STORE_MAP.values())

# 年なし日付も含めて複数の日程を取得（Part1・Part2 対応）
# 例: "2026年4月23日～4月27日" "4月30日～5月6日"
DATE_RE_ALL = re.compile(
    r"(?:(\d{4})年)?(\d{1,2})月(\d{1,2})日[^\d〜～\n]{0,10}[〜～]+\s*(?:(\d{1,2})月)?(\d{1,2})日"
)


def _parse_all_dates(text: str) -> list[tuple[str, str]]:
    """テキスト中のすべての日程範囲を返す（年なしは直前の年を引き継ぐ）"""
    results = []
    current_year = date.today().year
    for m in DATE_RE_ALL.finditer(text):
        try:
            if m.group(1):
                current_year = int(m.group(1))
            sm = int(m.group(2))
            sd = int(m.group(3))
            em = int(m.group(4)) if m.group(4) else sm
            ed = int(m.group(5))
            # 終了月が開始月より小さければ翌年とみなす
            end_year = current_year + 1 if em < sm else current_year
            start = date(current_year, sm, sd)
            end   = date(end_year,    em, ed) + timedelta(days=1)
            results.append((start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")))
        except ValueError:
            pass
    return results


def _scrape_article(url: str) -> list[Event]:
    """記事ページ1件をパースして Event を返す（対象外店舗は None）"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.encoding = resp.apparent_encoding
        soup = BeautifulSoup(resp.text, "html.parser")

        # ---- タイトル ----
        h1 = soup.find("h1")
        raw_title = h1.get_text(strip=True) if h1 else ""
        title = re.split(r"[|｜]", raw_title)[0].strip()
        if not title:
            return []

        # 店舗名・年を除去（長いキーを優先してマッチ）
        for key in sorted(STORE_MAP.keys(), key=len, reverse=True):
            title = title.replace(key, "")
        title = re.sub(r"\s*\d{4}\s*", " ", title).strip()

        # ---- 店舗名：主要コンテンツ先頭 1500 字に絞る ----
        main_el = (soup.find("article") or soup.find("main") or
                   soup.find(class_=re.compile(r"entry|content|post")) or soup.body)
        main_text = main_el.get_text(separator="\n", strip=True) if main_el else ""

        search_area = main_text[:1500]
        store = None
        for key, mapped in STORE_MAP.items():
            if key in search_area:
                store = mapped
                break
        if not store:
            return []

        # ---- 開催期間（複数日程対応: Part1・Part2 等）----
        date_ranges = _parse_all_dates(main_text)
        if not date_ranges:
            return []

        # ---- フロア ----
        floor = ""
        for line in main_text.split("\n"):
            line = line.strip()
            if len(line) > 40:
                continue
            if re.search(r"[1-9][0-9]?[階F]", line) and re.search(r"催|会場|場", line):
                floor = line
                break

        return [
            Event(store=store, title=title, start=s, end=e,
                  floor=floor, url=url, category="")
            for s, e in date_ranges
        ]
    except Exception as ex:
        print(f"[bussanten] article error {url}: {ex}", flush=True)
        return []


# 投稿スラッグ形式のパス（/word-word-2026/ など）のみ対象
_SLUG_RE = re.compile(r"^/[a-z][a-z0-9\-]+/$")


def scrape() -> list[Event]:
    events: list[Event] = []
    seen: set[str] = set()

    try:
        resp = requests.get(TOP_URL, headers=HEADERS, timeout=15)
        resp.encoding = resp.apparent_encoding
        soup = BeautifulSoup(resp.text, "html.parser")

        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"].rstrip("/") + "/"
            if not href.startswith(BASE_URL):
                continue
            path = href[len(BASE_URL):]
            if _SLUG_RE.match(path) and href not in seen:
                seen.add(href)
                links.append(href)

        print(f"[bussanten] {len(links)} article links found", flush=True)

        for url in links:
            time.sleep(1)
            events.extend(_scrape_article(url))

    except Exception as e:
        print(f"[bussanten] top page error: {e}", flush=True)

    print(f"[bussanten] raw events: {len(events)}", flush=True)
    return events
