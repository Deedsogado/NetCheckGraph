import re
import os
import time
import pytz
import datetime
import matplotlib.pyplot as plt
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Configuration
LOG_FILE = "netcheck.log"  # Update with your actual log filename
TIMEZONE = pytz.timezone("America/Denver")  # MST timezone

def parse_log(log_file):
    """Parse the log file and extract downtime events."""
    events = []
    with open(log_file, 'r') as f:
        content = f.readlines()

    down_time, up_time = None, None
    for line in content:
        down_match = re.search(r'LINK DOWN:\s+(.*)', line)
        up_match = re.search(r'LINK RECONNECTED:\s+(.*)', line)

        if down_match:
            down_time = convert_to_mst(down_match.group(1))
        elif up_match and down_time:
            up_time = convert_to_mst(up_match.group(1))
            events.append((down_time, up_time))
            down_time, up_time = None, None

    return events

def convert_to_mst(timestamp_str):
    """Convert a timestamp string to MST."""
    timestamp_formats = ["%a %d %b %Y %H:%M:%S %Z"]
    for fmt in timestamp_formats:
        try:
            dt = datetime.datetime.strptime(timestamp_str, fmt)
            if "UTC" in timestamp_str:
                dt = pytz.utc.localize(dt).astimezone(TIMEZONE)
            else:
                dt = TIMEZONE.localize(dt)
            return dt
        except ValueError:
            continue
    return None

def generate_timeline(events):
    """Generate a timeline graph from the events."""
    plt.figure(figsize=(10, 5))
    for down, up in events:
        plt.plot([down, up], [1, 1], color='red', linewidth=5)

    plt.xlabel("Time")
    plt.ylabel("Status")
    plt.title("Internet Downtime Timeline")
    plt.yticks([])
    plt.grid(True, axis='x')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig("netcheck_timeline.png")
    plt.close()
    print("Graph updated: netcheck_timeline.png")

class LogFileHandler(FileSystemEventHandler):
    """Watches for changes in the log file and updates the graph."""
    def on_modified(self, event):
        if event.src_path.endswith(LOG_FILE):
            print("Log file updated. Regenerating graph...")
            events = parse_log(LOG_FILE)
            generate_timeline(events)

if __name__ == "__main__":
    events = parse_log(LOG_FILE)
    generate_timeline(events)

    event_handler = LogFileHandler()
    observer = Observer()
    observer.schedule(event_handler, path=os.path.dirname(os.path.abspath(LOG_FILE)), recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
