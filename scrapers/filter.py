import re
from collections import defaultdict
from datetime import date, timedelta
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
    # 国・地域フェア（食品系催事として扱う）
    "イタリア", "フランス", "スペイン", "ドイツ", "イギリス", "ポルトガル",
    "ベルギー", "スイス", "オーストリア", "ギリシャ", "北欧",
    "アメリカ", "メキシコ", "ハワイ",
    "台湾", "韓国", "中国", "タイ", "ベトナム", "インド", "インドネシア",
    "トルコ", "モロッコ",
]

EXCLUDE_KEYWORDS = [
    "美術", "展覧", "アート", "ギャラリー", "ファッション",
    "コスメ", "化粧", "インテリア", "キッズ", "宝飾",
    "アクセサリー", "ジュエリー", "着物", "呉服", "陶芸",
    "書道", "工芸", "絵画", "彫刻", "写真展", "映画",
    "音楽", "クラシック", "文具", "雑貨", "家具",
    "ウィッグ", "かつら", "ヘアウィッグ",
    "真珠", "パール", "宝石", "ジュエル",
    # スポーツ・フィットネス系
    "ウォーキング", "ランニング", "スポーツ", "フィットネス", "ヨガ", "トレーニング",
    "アシックス", "ナイキ", "アディダス", "スニーカー", "シューズ", "スポーツウェア",
    # ファッション・アパレル系
    "アパレル", "ブランドバッグ", "バーゲン", "アウトレット", "婦人服", "紳士服", "婦人靴", "紳士靴",
    # 非食品マルシェ・クラフト系
    "クリエイター", "ハンドメイド", "クラフト", "手作り市", "フリーマーケット",
    # 催事ではないプロモーション・キャンペーン系
    "%オフ", "割引", "ポイント", "キャンペーン", "プレゼント",
    "サービスデー", "無料", "ご招待", "セール",
    # お知らせ・案内系（催事でなく情報告知）
    "おすすめ情報", "のご案内", "のご紹介", "お知らせ", "新着情報",
    # 単独店舗の出店告知（催事ではない）
    "初出店", "新規オープン", "グランドオープン", "リニューアルオープン",
]

FOOD_CATEGORIES = [
    "グルメ", "スイーツ", "フード", "デパ地下", "食品", "gourmet",
]

# 催事として扱う最低開催日数（これ未満は単発プロモーションとみなし除外）
MIN_EVENT_DAYS = 3


def is_food_event(event: Event) -> bool:
    text = f"{event.title} {event.category} {event.floor}"

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


def _is_recent(event: Event) -> bool:
    """終了日が7日以上前のイベントは除外（古いスクレイプデータ混入防止）"""
    try:
        return date.fromisoformat(event.end) >= date.today() - timedelta(days=7)
    except Exception:
        return True


def _extract_core_title(title: str) -> str:
    """冗長な前置き句を除去して催事名本体を返す。
    例: 「海明け 雪どけ ぐるめぐり 大北海道展」→「大北海道展」
        「雅に薫る 京の逸品 京都展」→「京都展」
    マッチしない場合はそのまま返す。"""
    matches = re.findall(r'\S+(?:展|博|フェア|マルシェ)', title)
    if matches:
        return max(matches, key=len)
    return title


def _normalize_title(title: str) -> str:
    """タイトルから週次・前後半などの suffix を除去して正規化する"""
    # ＜...＞ 【...】 <...> [...] （...） (...) を除去
    t = re.sub(r'[＜<【\[(（][^＞>】\])）]{0,30}[＞>】\])）]', '', title)
    # 末尾の空白・記号を除去
    t = re.sub(r'[\s　・｜|]+$', '', t).strip()
    return t[:20]


def filter_events(events: list[Event]) -> list[Event]:
    passed = [
        e for e in events
        if is_food_event(e) and _duration_days(e) >= MIN_EVENT_DAYS and _is_recent(e)
    ]

    # 同一店舗・タイトル先頭20字・開始日が同じものは重複とみなす
    seen: set[tuple] = set()
    unique = []
    for e in passed:
        key = (e.store, e.title[:20], e.start)
        if key not in seen:
            seen.add(key)
            unique.append(e)

    # 同一店舗・正規化タイトルが一致するイベントはひとつに統合する
    # （例: 北海道展＜1週目情報＞ + ＜2週目情報＞、イタリア展 Part1 + Part2）
    groups: dict[tuple, list[Event]] = defaultdict(list)
    for e in unique:
        key = (e.store, _normalize_title(e.title))
        groups[key].append(e)

    merged = []
    for (store, norm), group in groups.items():
        if len(group) == 1:
            merged.append(group[0])
        else:
            group_sorted = sorted(group, key=lambda e: e.start)
            base = group_sorted[0]
            min_start = min(e.start for e in group)
            max_end   = max(e.end   for e in group)
            clean_title = re.sub(
                r'[＜<【\[(（][^＞>】\])）]{0,30}[＞>】\])）]', '', base.title
            ).strip()
            merged.append(Event(
                store=base.store, title=clean_title,
                start=min_start,  end=max_end,
                floor=base.floor, url=base.url, category=base.category,
            ))

    # 全イベントのタイトルから冗長な前置き句を除去
    result = []
    for e in merged:
        core = _extract_core_title(e.title)
        if core != e.title:
            e = Event(store=e.store, title=core, start=e.start, end=e.end,
                      floor=e.floor, url=e.url, category=e.category)
        result.append(e)
    return result
