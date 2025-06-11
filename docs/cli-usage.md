# Task Time Tracker (TTT) CLI Documentation

Task Time Tracker is a command-line tool that helps you log, view, and summarize time spent on various tasks. This document provides a guide to using the TTT CLI.

## Installation

### Prerequisites
- Python 3.6 or higher

### Setup
1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/task-time-tracker.git
   cd task-time-tracker
   ```

2. No dependencies required to run the basic CLI.

## Running the CLI

The main command format is:

```bash
python main.py <command> [options]
```

## Commands

### `log`

Records time spent on a task.

```bash
python main.py log <task> <duration> [options]
```

Parameters:
- `task`: (Required) Name of the task you worked on
- `duration`: (Required) Time spent on the task in minutes

Options:
- `-d, --description`: Description of what was done
- `--date`: Date of the task (YYYY-MM-DD), defaults to today

Examples:
```bash
# Log 45 minutes spent on fixing bugs
python main.py log "Fix bugs" 45

# Log with description
python main.py log "Write docs" 30 -d "Created API documentation"

# Log with specific date
python main.py log "Code review" 60 --date 2023-04-15
```

### `view`

Displays time entries with optional filtering.

```bash
python main.py view [options]
```

Options:
- `-t, --task`: Filter entries by task name
- `-d, --date`: Filter entries by date (YYYY-MM-DD)
- `-l, --limit`: Limit the number of entries shown

Examples:
```bash
# View all time entries
python main.py view

# View entries for a specific task
python main.py view -t "Fix bugs"

# View entries for a specific date
python main.py view -d 2023-04-15

# Limit to last 10 entries
python main.py view -l 10
```

### `summary`

Generates a summary report of tracked time.

```bash
python main.py summary [options]
```

Options:
- `--from-date`: Start date for summary (YYYY-MM-DD)
- `--to-date`: End date for summary (YYYY-MM-DD)
- `-g, --group-by`: Group summary by category (task, day, week, month)

Examples:
```bash
# Summarize all time entries by task
python main.py summary

# Summarize entries for a date range
python main.py summary --from-date 2023-04-01 --to-date 2023-04-30

# Summarize entries grouped by week
python main.py summary -g week
```

## Global Flags

The following flags can be used with any command:

### `--help`

Displays help information for the CLI or a specific command.

```bash
python main.py --help
python main.py log --help
```

### `--version`

Displays the current version of the Task Time Tracker.

```bash
python main.py --version
```

### `--config`

Specifies a configuration file to use.

```bash
python main.py log "Fix bugs" 45 --config settings.json
```

### `--debug`

Enables debug mode, displaying additional information useful for troubleshooting.

```bash
python main.py log "Fix bugs" 45 --debug
```

## Combined Examples

You can combine commands with global flags for more advanced usage:

```bash
# Log time with debugging enabled
python main.py log "Fix bugs" 45 --category dev --debug

# View entries with a custom config
python main.py view -t "Fix bugs" --config custom.json

# Generate a summary in debug mode
python main.py summary -g week --debug
```

## Notes

- Time is tracked in minutes.
- Dates should be in YYYY-MM-DD format.
- When no date is specified, the current date is used.
- The `--help` flag can be used with any command to get command-specific help.
```