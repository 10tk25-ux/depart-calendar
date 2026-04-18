from .base import Event

INCLUDE_KEYWORDS = [
    "グルメ", "食品", "フード", "スイーツ", "菓子", "物産", "産地",
    "北海道", "九州", "東北", "関西", "四国", "中国", "沖縄", "東京",
    "地方", "弁当", "デパ地下", "惣菜", "フルーツ", "野菜", "肉",
    "魚介", "海産", "海鮮", "パン", "チーズ", "ワイン", "日本酒",
    "ビール", "食", "味覚", "美食", "和菓子", "洋菓子", "ケーキ",
    "チョコ", "アイス", "ラーメン", "寿司", "天ぷら", "牛", "豚",
    "鶏", "米", "麺", "そば", "うどん", "餅", "大福", "せんべい",
    "味噌", "醤油", "だし", "鍋", "焼肉", "バーベキュー", "BBQ",
    "農産", "畜産", "水産", "食材", "調味料", "スパイス",
]

EXCLUDE_KEYWORDS = [
    "美術", "展覧", "アート", "ギャラリー", "ファッション",
    "コスメ", "化粧", "インテリア", "キッズ", "宝飾",
    "アクセサリー", "ジュエリー", "着物", "呉服", "陶芸",
    "書道", "工芸", "絵画", "彫刻", "写真展", "映画",
    "音楽", "クラシック", "文具", "雑貨", "家具",
]

FOOD_CATEGORIES = [
    "グルメ", "スイーツ", "食", "フード", "デパ地下", "gourmet",
]


def is_food_event(event: Event) -> bool:
    text = f"{event.title} {event.category}".lower()

    for kw in EXCLUDE_KEYWORDS:
        if kw in text:
            return False

    for kw in INCLUDE_KEYWORDS:
        if kw in text:
            return True

    for kw in FOOD_CATEGORIES:
        if kw.lower() in text:
            return True

    return False


def filter_events(events: list[Event]) -> list[Event]:
    return [e for e in events if is_food_event(e)]
