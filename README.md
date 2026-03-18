# SharpTracker

SharpTracker is a Streamlit app for tracking sports wagers, bankroll activity, and performance analytics per user.

## Features

- Secure user login with credentials stored in Streamlit secrets
- Wager logging for singles and multi-match tickets
- Bet settlement and history management
- Bankroll transaction tracking
- Dashboard analytics for profit, ROI, hit rate, streaks, and breakdowns
- User settings for sports, leagues, bookies, bet types, and tipsters
- One-click deletion of user wager/bankroll data while keeping settings

## Tech Stack

- Python
- Streamlit
- Pandas
- Plotly
- Google Sheets via `st-gsheets-connection`

## Project Structure

```text
.
├── app.py
├── auth.py
├── styling.py
├── data/
│   ├── analytics.py
│   └── data_layer.py
└── views/
    ├── bankroll.py
    ├── dashboard.py
    ├── settings.py
    └── wagers.py
```

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Configure Streamlit secrets for:
   - `users`: a username/password mapping
   - `connections.gsheets`: your Google Sheets connection settings

3. Run the app:

```bash
streamlit run app.py
```

## Notes

- Each user reads and writes to their own Google Sheets tabs:
  - `bets_<username>`
  - `cash_<username>`
  - `meta_<username>`
- Changes can be made locally in the UI and then pushed to the cloud with Sync.

## License

MIT. See [LICENSE](LICENSE).
