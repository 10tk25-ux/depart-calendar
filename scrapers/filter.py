from datetime import date
from .base import Event

INCLUDE_KEYWORDS = [
    "グルメ", "食品", "フード", "スイーツ", "菓子", "物産", "産地",
    "北海道", "九州", "東北", "関西", "四国", "中国", "沖縄",
    "弁当", "デパ地下", "惣菜", "フルーツ", "野菜",
    "魚介", "海産", "海鮮", "パン", "チーズ", "ワイン", "日本酒",
    "ビール", "味覚", "美食", "和菓子", "洋菓子", "ケーキ",
    "チョコ", "アイス", "ラーメン", "寿司", "天ぷら",
    "麺", "そば", "うどん", "餅", "大福", "せんべい",
    "味噌", "醤油", "だし", "鍋", "焼肉",
    "農産", "畜産", "水産", "食材", "調味料",
    "展", "フェア", "マルシェ", "市場",
]

EXCLUDE_KEYWORDS = [
    "美術", "展覧", "アート", "ギャラリー", "ファッション",
    "コスメ", "化粧", "インテリア", "キッズ", "宝飾",
    "アクセサリー", "ジュエリー", "着物", "呉服", "陶芸",
    "書道", "工芸", "絵画", "彫刻", "写真展", "映画",
    "音楽", "クラシック", "文具", "雑貨", "家具",
    # 催事ではないプロモーション・キャンペーン系
    "%オフ", "割引", "ポイント", "キャンペーン", "プレゼント",
    "サービスデー", "無料", "ご招待", "セール",
    # お知らせ・案内系（催事でなく情報告知）
    "おすすめ情報", "ショップのご案内", "のご案内", "お知らせ",
    "ご紹介", "新着情報",
]

FOOD_CATEGORIES = [
    "グルメ", "スイーツ", "フード", "デパ地下", "食品", "gourmet",
]

# 催事として扱う最低開催日数（これ未満は単発プロモーションとみなし除外）
MIN_EVENT_DAYS = 3


def is_food_event(event: Event) -> bool:
    text = f"{event.title} {event.category}"

    for kw in EXCLUDE_KEYWORDS:
        if kw in text:
            return False

    for kw in INCLUDE_KEYWORDS:
        if kw in text:
            return True

    for kw in FOOD_CATEGORIES:
        if kw in text:
            return True

    return False


def _duration_days(event: Event) -> int:
    """イベントの開催日数を返す（取得失敗時は999で通過させる）"""
    try:
        return (date.fromisoformat(event.end) - date.fromisoformat(event.start)).days
    except Exception:
        return 999


def filter_events(events: list[Event]) -> list[Event]:
    return [
        e for e in events
        if is_food_event(e) and _duration_days(e) >= MIN_EVENT_DAYS
    ]
