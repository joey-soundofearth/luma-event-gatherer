import json
import csv
from dateutil import parser
import sys


def events_jsonl_to_csv(input_file: str, output_file: str):
    with open(input_file, "r") as infile, open(output_file, "w", newline="") as outfile:
        writer = csv.writer(outfile)
        writer.writerow(
            [
                "Title",
                "Event Image",
                "Tags",
                "Registrations",
                "Internal/External",
                "Event Link",
                "Start Date",
                "End Date",
                "Total Time",
                "Venue",
                "Organizer",
            ]
        )

        for line in infile:
            data = json.loads(line)
            event = data.get("event", {})
            platform = data.get("platform", "")
            event_url = event.get("url", "")
            if platform == "luma":
                event_url = f"https://luma.com/{event_url}"

            start_at = event.get("start_at", "")
            end_at = event.get("end_at", "")
            if start_at and end_at:
                total_time = parser.isoparse(end_at) - parser.isoparse(start_at)
            else:
                total_time = ""

            geo_addr_info = event.get("geo_address_info") or {}
            venue = geo_addr_info.get("address", "")

            hosts = data.get("hosts", [])
            if hosts:
                host = hosts[0]
                name = host.get("name", "")
            else:
                name = ""

            writer.writerow(
                [
                    event.get("name", ""),
                    event.get("cover_url", ""),
                    [tag.get("name", "") for tag in data.get("tags", [])],
                    data.get("ticket_count", ""),
                    platform,
                    event_url,
                    start_at,
                    end_at,
                    total_time,
                    venue,
                    name,
                ]
            )


if __name__ == "__main__":
    if len(sys.argv) > 1 and len(sys.argv) != 3:
        print("Usage: python format.py [input_jsonl_file] [output_csv_file]")
        print("       If no arguments are given, defaults for LACW used.")
        sys.exit(1)

    if len(sys.argv) == 3:
        input_file = sys.argv[1]
        output_file = sys.argv[2]
    else:
        input_file = "luma_lacw_data.jsonl"
        output_file = "luma_lacw_data.csv"

    events_jsonl_to_csv(input_file, output_file)
