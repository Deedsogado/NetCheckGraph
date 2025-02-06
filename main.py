import logging
import re
import os
import time
import pytz
import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
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
    for line in content:
        down_match = re.search(r'LINK DOWN:\s+(.*)', line)
        up_match = re.search(r'LINK RECONNECTED:\s+(.*)', line)

        if down_match:
            down_time = convert_to_mst(down_match.group(1))
        elif up_match and down_time:
            up_time = convert_to_mst(up_match.group(1))
            events.append((down_time, 0))  # Down event
            events.append((up_time, 1))    # Up event
            down_time = None

    return sorted(events, key=lambda x: x[0])

def convert_to_mst(timestamp_str):
    """Convert a timestamp string to MST."""
    try:
        parts = timestamp_str.rsplit(" ", 1)  # Remove time zone abbreviation
        dt = datetime.datetime.strptime(parts[0], "%a %d %b %Y %H:%M:%S")
        if "UTC" in timestamp_str:
            dt = pytz.utc.localize(dt).astimezone(TIMEZONE)
        else:
            dt = TIMEZONE.localize(dt)
        return dt
    except ValueError as e:
        logging.error(f"Error parsing timestamp: {timestamp_str} - {e}")
        return None

def generate_timeline(events):
    """Generate a seismograph-like timeline graph, with each day on its own row."""
    if not events:
        return

    # Organize events by day
    daily_events = {}
    for t, s in events:
        date = t.date()
        if date not in daily_events:
            daily_events[date] = []
        daily_events[date].append((t, s))

    # Sort days chronologically
    sorted_dates = sorted(daily_events.keys())
    num_days = len(sorted_dates)

    fig, axes = plt.subplots(num_days, 1, figsize=(12, 2 * num_days), sharex=True, sharey=True)
    if num_days == 1:
        axes = [axes]

    for ax, date in zip(axes, sorted_dates):
        times, statuses = zip(*daily_events[date])
        ax.step(times, statuses, where='post', color='red', linewidth=2)
        ax.set_ylabel(date.strftime('%a %b %d'))
        ax.yticks([-1, 2], labels=["Down", "Up"])
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax.grid(True, axis='x')

    plt.xlabel("Time (MST)")
    plt.suptitle("Internet Uptime vs. Downtime Timeline")
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
