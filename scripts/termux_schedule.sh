#!/data/data/com.termux/files/usr/bin/sh
# Schedule FXBOT runs in Termux (forward testing, module 82).
#
#   sh scripts/termux_schedule.sh          # install: run every hour at :07 on weekdays
#   sh scripts/termux_schedule.sh --remove # remove the schedule
#
# Needs: pkg install cronie termux-services  (then restart Termux once)
# Optional phone notifications: install the Termux:API app + pkg install termux-api
# The phone must not kill Termux: run `termux-wake-lock` or allow background activity.

set -e
PROJECT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="$(command -v python)"
LINE="7 * * * 1-5 cd $PROJECT && $PYTHON fxbot.py run --notify >> $PROJECT/data/cron_run.log 2>&1"
FUND="17 6 * * * cd $PROJECT && $PYTHON fxbot.py fundamentals --days 30 >> $PROJECT/data/cron_fund.log 2>&1"
ADAPT="35 21 * * 1-5 cd $PROJECT && $PYTHON fxbot.py adaptive --lock >> $PROJECT/data/cron_adaptive.log 2>&1"
S75="40 21 * * 1-5 cd $PROJECT && $PYTHON fxbot.py signals75 --lock >> $PROJECT/data/cron_signals75.log 2>&1"

if [ "$1" = "--remove" ]; then
    crontab -l 2>/dev/null | grep -v "fxbot.py" | crontab -
    echo "FXBOT planovani odstraneno"
    exit 0
fi

command -v crontab >/dev/null || { echo "chybi cron: pkg install cronie termux-services"; exit 1; }
(crontab -l 2>/dev/null | grep -v "fxbot.py"; echo "$LINE"; echo "$FUND"; echo "$ADAPT"; echo "$S75") | crontab -
sv-enable crond 2>/dev/null || crond
echo "FXBOT bezi kazdou hodinu v :07 (po-pa), fundamenty denne v 06:17, adaptivni vyzyvatel v 21:35 a system 75+ v 21:40 (cas telefonu)"
crontab -l | grep fxbot
