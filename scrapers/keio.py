import re
import requests
from bs4 import BeautifulSoup
from datetime import date, timedelta
from .base import Event

EVENT_URL = "https://www.keionet.com/info/shinjuku/topics/000231.html"
STORE = "京王新宿"
BASE_URL = "https://www.keionet.com"

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# 食品・物産系と判断するヒントキーワード（これを1つも含まない催事は除外）
_FOOD_HINTS = {
    "グルメ", "食", "スイーツ", "菓子", "パン", "物産", "産地", "フード",
    "北海道", "九州", "東北", "関西", "四国", "中国", "沖縄",
    "イタリア", "フランス", "スペイン", "台湾", "韓国", "アジア",
    "京都", "大阪", "名古屋", "福岡", "札幌", "仙台", "広島", "金沢",
    "逸品", "名産", "特産", "銘品", "産直", "郷土",
    "弁当", "惣菜", "ワイン", "日本酒", "ビール", "チーズ",
    "和菓子", "洋菓子", "ケーキ", "チョコ",
}

# "4/16(木)　→　22(水)" や "4/24(金)　→　5/6(水・振休)"
DATE_RE = re.compile(
    r"(\d{1,2})/(\d{1,2})[^\d→〜～]*[→〜～]+\s*(?:(\d{1,2})/)?(\d{1,2})"
)


def _parse_date(text: str, base_year: int) -> tuple[str, str]:
    m = DATE_RE.search(text)
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


def scrape() -> list[Event]:
    events: list[Event] = []
    try:
        resp = requests.get(EVENT_URL, headers=HEADERS, timeout=15)
        resp.encoding = resp.apparent_encoding
        soup = BeautifulSoup(resp.text, "html.parser")

        current_year = date.today().year

        # 月ヘッダーとイベントブロックをドキュメント順に処理
        for tag in soup.find_all("div"):
            classes = tag.get("class", [])

            if "p-topicsEvent__month" in classes:
                m = re.search(r"(\d{4})年", tag.get_text())
                if m:
                    current_year = int(m.group(1))

            elif "p-topicsEvent__container" in classes:
                date_el = tag.find(class_="date01")
                if not date_el:
                    continue
                start, end = _parse_date(date_el.get_text(), current_year)
                if not start:
                    continue

                txt_el = tag.find(class_="p-topicsEvent__Txt01")
                if not txt_el:
                    continue

                # ■ 区切りで各イベントを分離
                # リンクごとにタイトルとURLを抽出
                seen = set()
                for a in txt_el.find_all("a", href=True):
                    title = a.get_text(strip=True).lstrip("■").strip()
                    if not title or title in seen:
                        continue
                    seen.add(title)
                    if not any(kw in title for kw in _FOOD_HINTS):
                        continue
                    href = a["href"]
                    url = href if href.startswith("http") else BASE_URL + href
                    events.append(Event(
                        store=STORE, title=title, start=start, end=end,
                        url=url, floor="7F大催事場", category="",
                    ))

                # リンクなしの ■ 項目も取得
                full_text = txt_el.get_text(separator="\n", strip=True)
                for line in full_text.split("\n"):
                    line = line.strip().lstrip("■").strip()
                    if not line or line.startswith("※") or line in seen:
                        continue
                    seen.add(line)
                    if not any(kw in line for kw in _FOOD_HINTS):
                        continue
                    events.append(Event(
                        store=STORE, title=line, start=start, end=end,
                        url=EVENT_URL, floor="7F大催事場", category="",
                    ))

    except Exception as e:
        print(f"[keio] scrape error: {e}", flush=True)

    print(f"[keio] raw events: {len(events)}", flush=True)
    return events
