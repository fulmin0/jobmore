# Jobmore — Job Discovery Automation

Jobmore scrapes job boards daily, deduplicates and scores results against your preferences, writes structured Markdown reports, and optionally sends a Slack digest. Configure once, run automatically.

## Requirements

- Python 3.11+
- macOS is required for launchd automation; scripts run on any OS for manual use

## Install

```bash
git clone <repo-url> jobmore
cd jobmore
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Config

```bash
cp config.example.json config.json
```

Open `config.json` and fill in:

| Field | Required | Notes |
|-------|----------|-------|
| `location.based_in` | Yes | Your city/state |
| `location.search_location` | Yes | Search geography passed to job boards (e.g. `"India"`) |
| `target_roles` | Yes | List of role titles used as search terms |
| `compensation.minimum_salary_lpa` | Yes | Minimum acceptable salary (used in scoring) |
| `slack.webhook_url` | Optional | Slack incoming webhook URL |
| `slack.enabled` | Optional | Set `true` to enable Slack notifications |
| `output.md_path` | Optional | Absolute path for Markdown output (e.g. an Obsidian vault folder). Leave empty to write to `output/` inside the project. |

All other fields (scoring weights, discovery settings, domain/company preferences) have sensible defaults you can tune later.

## Run

```bash
# Activate virtual environment
source venv/bin/activate

# Test mode — fewer results, verbose output
python scripts/discover.py --test

# Full run
python scripts/discover.py
```

## Output

By default all output goes inside the project directory:

```
data/              # jobs_found.json — full job database
output/
  data/
    jobs_found.md      # Human-readable top-25 active jobs
    discovery_log.md   # Run history and source reliability
    source_reliability.json
  job_details/         # One .md file per job (top 25 each run)
archive/           # Expired jobs (auto-archived after retention_days)
logs/              # stdout/stderr from launchd runs
```

Set `output.md_path` in `config.json` to redirect the `output/` tree to a custom location, such as an Obsidian vault folder.

## Automate (macOS)

```bash
# Copy the template and replace YOUR_USERNAME with your macOS username
cp com.jobmore.discover.plist.example com.jobmore.discover.plist
# Edit the file — replace all four occurrences of YOUR_USERNAME
nano com.jobmore.discover.plist

# Install and start the agent (runs daily at 07:30 local time)
cp com.jobmore.discover.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.jobmore.discover.plist
```

Logs are written to `logs/discover.log` and `logs/discover.error.log`.

To stop the agent:
```bash
launchctl unload ~/Library/LaunchAgents/com.jobmore.discover.plist
```

## Roadmap

- **Phase 1 (done):** Daily discovery, deduplication, scoring, Markdown reports, Slack digest, launchd automation
- **Phase 2:** Resume/profile integration — score jobs against detailed work history; AI match explanations
- **Phase 3:** Application tracking — status workflow, follow-up reminders
- **Phase 4:** Outreach automation — draft recruiter messages, track conversations
