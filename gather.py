import requests
from enum import Enum
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import json
import sys
import keyboard

# Get event call:
# https://api2.luma.com/event/get?event_api_id=evt-Cbk809MaW98Be8g


class FetchResult(Enum):
    NO_MORE = 0
    RATE_LIMIT = 1
    HTTP_ERROR = 2
    ETC_ERROR = 3
    SUCCESS = 4


retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE"],
)
adapter = HTTPAdapter(max_retries=retry_strategy)


class LumaEventFetcher:
    def __init__(self, calendar_id: str, period: str):
        self.calendar_id = calendar_id
        self.period = period
        self.cursor = ""
        self.has_more = True
        self.base_url = "https://api2.luma.com/calendar/get-items"
        self.session = requests.Session()
        self.session.mount("https://", adapter)

    def fetch_events(self, limit: int = 20):
        if not self.has_more:
            return (FetchResult.NO_MORE, "")

        params: dict[str, str | int] = {
            "calendar_api_id": self.calendar_id,
            "pagination_limit": limit,
        }
        if self.period:
            params["period"] = self.period
        if self.cursor:
            params["pagination_cursor"] = self.cursor

        try:
            response = self.session.get(self.base_url, params=params)
            response.raise_for_status()
        except requests.exceptions.HTTPError as http_err:
            if http_err.response.status_code == 429:
                return (FetchResult.RATE_LIMIT, str(http_err))
            else:
                return (FetchResult.HTTP_ERROR, str(http_err))
        except Exception as err:
            return (FetchResult.ETC_ERROR, str(err))

        data = response.json()
        self.cursor = data.get("next_cursor")
        self.has_more = data.get("has_more", False)
        entries = data.get("entries", [])
        return (FetchResult.SUCCESS, entries)

    def restore_state(self, state: dict[str, str | bool]):
        self.has_more = state.get("has_more", True)
        self.cursor = state.get("cursor", "")
        self.period = state.get("period", "past")

    def serialize(self):
        state = {
            "has_more": self.has_more,
            "cursor": self.cursor,
            "period": self.period,
        }
        return state


class LumaPastEventGatherer:
    def __init__(self, calendar_id: str, save_file: str, data_file: str):

        self.calendar_id = calendar_id
        self.save_file = save_file
        self.data_file = data_file
        self.gathered_event_ids: set[str] = set()
        self.fetcher = LumaEventFetcher(self.calendar_id, "past")
        self.restore_state()

    def save_entry(self, entry: dict):
        with open(self.data_file, "a") as f:
            json.dump(entry, f)
            f.write("\n")

    def handle_fetch_result(self, result: FetchResult, data, false_on_regather: bool):
        if result == FetchResult.NO_MORE:
            print("No more events to fetch.")
            return False
        elif result == FetchResult.RATE_LIMIT:
            print("Rate limited. Stopping fetch.")
            return False
        elif result in (FetchResult.HTTP_ERROR, FetchResult.ETC_ERROR):
            print(f"Error occurred: {data}. Stopping fetch.")
            return False
        elif result == FetchResult.SUCCESS:
            for entry in data:
                if not isinstance(entry, dict):
                    continue
                event = entry.get("event")
                if not event:
                    continue
                api_id = event.get("api_id")
                if api_id in self.gathered_event_ids:
                    if false_on_regather:
                        return False
                    else:
                        continue
                self.gathered_event_ids.add(api_id)
                self.save_entry(entry)
                self.save_state()
            return True
        else:
            print("Unknown fetch result. Stopping fetch.")
            return False

    def check_quit(self):
        if keyboard.is_pressed("q"):
            print("Quit signal received. Stopping fetch.")
            return True
        return False

    def gather_events(self, recent_refetch: bool = True):
        if recent_refetch and self.fetcher.cursor != "":
            print("Checking for recently past events...")

            recent_fetcher = LumaEventFetcher(self.calendar_id, "past")
            cont = True
            scount = len(self.gathered_event_ids)

            while cont:
                result, data = recent_fetcher.fetch_events(limit=20)
                cont = (
                    self.handle_fetch_result(result, data, True)
                    and not self.check_quit()
                )

            print(f"Got {len(self.gathered_event_ids) - scount} new events.")

        cont = True
        while cont:
            result, data = self.fetcher.fetch_events(limit=20)
            cont = (
                self.handle_fetch_result(result, data, False) and not self.check_quit()
            )
            print(f"Total gathered events: {len(self.gathered_event_ids)}")
        self.save_state()

    def restore_state(self):
        try:
            with open(self.save_file, "r") as f:
                state = json.load(f)
                self.fetcher.restore_state(state.get("fetcher", {}))
                self.gathered_event_ids = set(state.get("gathered_event_ids", []))
        except FileNotFoundError:
            pass

    def serialize(self):
        state: dict = {
            "fetcher": self.fetcher.serialize(),
            "gathered_event_ids": list(self.gathered_event_ids),
        }
        return state

    def save_state(self):
        state = self.serialize()
        with open(self.save_file, "w") as f:
            json.dump(state, f)


if __name__ == "__main__":
    if len(sys.argv) > 1 and len(sys.argv) != 4:
        print("Usage: python gather.py [calendar_id] [save_file] [data_file]")
        print("       If no arguments are given, default values for LACW used.")
        sys.exit(1)

    if len(sys.argv) == 4:
        calendar_id = sys.argv[1]
        save_file = sys.argv[2]
        data_file = sys.argv[3]
        gatherer = LumaPastEventGatherer(calendar_id, save_file, data_file)
        gatherer.gather_events()
    else:
        gatherer = LumaPastEventGatherer(
            "cal-Ef226o3nBV69y33", "luma_lacw_state.json", "luma_lacw_data.jsonl"
        )
        gatherer.gather_events()
