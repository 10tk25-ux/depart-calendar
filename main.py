import json
import sys
from pathlib import Path
from scrapers import tobu, keio, bussanten
from scrapers import departevent
from scrapers.filter import filter_events

OUTPUT_PATH = Path(__file__).parent / "data" / "events.json"


def run():
    all_events = []

    scrapers = [
        ("東武池袋",  tobu.scrape),
        ("京王新宿",  keio.scrape),
        # bussanten.info: 伊勢丹新宿・日本橋三越・新宿高島屋の催事場イベントを取得
        ("bussanten", bussanten.scrape),
        # departevent.net: bussan.html で物産展系を補完
        ("新宿高島屋", departevent.scrape_takashimaya),
        ("日本橋三越", departevent.scrape_mitsukoshi),
    ]

    for name, fn in scrapers:
        print(f"[{name}] scraping...", flush=True)
        try:
            events = fn()
            print(f"[{name}] {len(events)} events found", flush=True)
            all_events.extend(events)
        except Exception as e:
            print(f"[{name}] ERROR: {e}", flush=True)

    print(f"\nTotal before filter: {len(all_events)}", flush=True)
    food_events = filter_events(all_events)
    print(f"Total after food filter: {len(food_events)}", flush=True)

    OUTPUT_PATH.parent.mkdir(exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump([e.to_dict() for e in food_events], f, ensure_ascii=False, indent=2)

    print(f"\nSaved to {OUTPUT_PATH}", flush=True)


if __name__ == "__main__":
    run()
