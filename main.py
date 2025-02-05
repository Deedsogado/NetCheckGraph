import re
import os
import time
import pytz
import datetime
import matplotlib.pyplot as plt
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Configuration
LOG_FILE = "connection_log.txt"  # Update with your actual log filename
TIMEZONE = pytz.timezone("America/Denver")  # MST timezone

def parse_log(log_file):
    """Parse the log file and extract uptime and downtime events."""
    events = []
    with open(log_file, 'r') as f:
        content = f.readlines()

    down_time = None
    start_time = None
    end_time = None
    for line in content:
        down_match = re.search(r'LINK DOWN:\s+(.*)', line)
        up_match = re.search(r'LINK RECONNECTED:\s+(.*)', line)

        if down_match:
            down_time = convert_to_mst(down_match.group(1))
            if not start_time:
                start_time = down_time
        elif up_match and down_time:
            up_time = convert_to_mst(up_match.group(1))
            events.append((down_time, 0))  # Down event
            events.append((up_time, 1))    # Up event
            down_time = None
            end_time = up_time

    if start_time and end_time:
        events.insert(0, (start_time - datetime.timedelta(minutes=1), 1))  # Assume it was up before first recorded event
        events.append((end_time + datetime.timedelta(minutes=1), 1))  # Assume it remained up after last event

    return sorted(events, key=lambda x: x[0])

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
    times, statuses = zip(*events)
    plt.figure(figsize=(48, 5))
    plt.step(times, statuses, where='post', color='red', linewidth=2, label='Internet Status')

    plt.xlabel("Time")
    plt.ylabel("Status (1 = Up, 0 = Down)")
    plt.title("Internet Uptime vs. Downtime Timeline")
    plt.yticks([0, 1], labels=["Down", "Up"])
    plt.grid(True, axis='x')
    plt.xticks(rotation=45)
    plt.legend()
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
