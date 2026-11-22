"""The one hard-coded demo user (login is out of scope for this assignment).

This is demo data, not real personal data: a student in Madrid with a few weekly classes.
Times are local to the user's time zone.
"""

from datetime import time

from app.windows import BusyBlock, Person

DEMO_USER = Person(
    tz="Europe/Madrid",
    sleep_start=time(23, 0),
    sleep_end=time(7, 0),
    busy=(
        BusyBlock(weekday=0, start=time(9, 0), end=time(11, 0)),  # Monday class
        BusyBlock(weekday=1, start=time(9, 30), end=time(12, 30)),  # Tuesday class
        BusyBlock(weekday=2, start=time(9, 0), end=time(11, 0)),  # Wednesday class
        BusyBlock(weekday=3, start=time(9, 30), end=time(12, 30)),  # Thursday class
    ),
)
