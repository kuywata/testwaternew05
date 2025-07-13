name: In Buri Bridge River Alert

on:
  workflow_dispatch:
  schedule:
    - cron: '*/15 * * * *'

permissions:
  contents: write

jobs:
  scrape:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install requests pytz

      - name: Run Alert Script
        env:
          LINE_CHANNEL_ACCESS_TOKEN: ${{ secrets.LINE_CHANNEL_ACCESS_TOKEN }}
          LINE_TARGET_ID: ${{ secrets.LINE_TARGET_ID }}
        run: python inburi_bridge_alert.py

      - name: Commit and push if data changed
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add inburi_bridge_data.json
          git diff --staged --quiet || git commit -m "Update In Buri bridge water level data" && git push
