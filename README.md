## Gather

Run the past event gathering script with: `python gatherer.py [calendar_id] [save_file] [data_file]`

If run with no arguments it will get LACW events with save file "luma_lacw_state.json" and data file "luma_lacw_data.jsonl".

The gatherer is stateful, so we can stop it at any time by holding down the 'q' key and resume gathering by running the program again (this is generally not necessary because there is never a HUGE amount of events to gather)

Rerunning will gather new past events that have passed after the last run.

## Format

After gathering the raw event data it can be formatted into a csv with the headers that we want to keep: `python format.py [input_jsonl_file] [output_csv_file]`

Again if no arguments are provided we will use the default LACW values: "luma_lacw_data.csv".
