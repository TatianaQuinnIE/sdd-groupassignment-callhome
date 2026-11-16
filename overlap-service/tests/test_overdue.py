from datetime import UTC, datetime, timedelta, timezone

import pytest

from app.overdue import CallHistory, Overdue, overdue_status, rank_by_overdue

NOW = datetime(2026, 11, 16, 12, 0, tzinfo=UTC)


def days_ago(days: float) -> datetime:
    return NOW - timedelta(days=days)


def ids(ranked):
    return [r.contact_id for r in ranked]


def test_never_called_is_due_and_has_no_ratio():
    status = overdue_status(None, 7, NOW)
    assert status == Overdue(days_since=None, ratio=None, is_due=True)


def test_recent_call_is_not_due_yet():
    status = overdue_status(days_ago(3), 7, NOW)
    assert status.days_since == pytest.approx(3.0)
    assert status.ratio == pytest.approx(3 / 7)
    assert status.is_due is False


def test_due_exactly_on_the_day():
    status = overdue_status(days_ago(7), 7, NOW)
    assert status.ratio == pytest.approx(1.0)
    assert status.is_due is True


def test_future_call_counts_as_just_now():
    status = overdue_status(NOW + timedelta(hours=2), 7, NOW)
    assert status.days_since == 0.0
    assert status.ratio == 0.0
    assert status.is_due is False


def test_partial_days_are_counted():
    status = overdue_status(NOW - timedelta(hours=36), 3, NOW)
    assert status.days_since == pytest.approx(1.5)
    assert status.ratio == pytest.approx(0.5)


def test_timezones_do_not_change_the_result_for_the_same_instant():
    seoul = timezone(timedelta(hours=9))
    same_instant = days_ago(5).astimezone(seoul)
    assert overdue_status(same_instant, 7, NOW) == overdue_status(days_ago(5), 7, NOW)


@pytest.mark.parametrize("every", [0, -3])
def test_non_positive_frequency_is_rejected(every):
    with pytest.raises(ValueError, match="call_every_days"):
        overdue_status(days_ago(1), every, NOW)


def test_naive_datetimes_are_rejected():
    with pytest.raises(ValueError, match="now must be timezone-aware"):
        overdue_status(None, 7, datetime(2026, 11, 16))

    with pytest.raises(ValueError, match="last_called must be timezone-aware"):
        overdue_status(datetime(2026, 11, 1), 7, NOW)


def test_never_called_contacts_rank_first():
    contacts = [
        CallHistory(1, 7, days_ago(100)),
        CallHistory(2, 7, None),
        CallHistory(3, 7, days_ago(8)),
    ]
    assert ids(rank_by_overdue(contacts, NOW)) == [2, 1, 3]


def test_rank_uses_ratio_not_raw_days():
    contacts = [
        CallHistory(1, 30, days_ago(40)),
        CallHistory(2, 1, days_ago(3)),
    ]
    assert ids(rank_by_overdue(contacts, NOW)) == [2, 1]


def test_due_contacts_come_before_not_due_ones():
    contacts = [
        CallHistory(1, 7, days_ago(2)),
        CallHistory(2, 7, days_ago(9)),
        CallHistory(3, 7, days_ago(5)),
    ]
    assert ids(rank_by_overdue(contacts, NOW)) == [2, 3, 1]


def test_ties_are_broken_by_contact_id():
    contacts = [
        CallHistory(5, 7, days_ago(7)),
        CallHistory(2, 14, days_ago(14)),
        CallHistory(9, 7, None),
        CallHistory(4, 7, None),
    ]
    assert ids(rank_by_overdue(contacts, NOW)) == [4, 9, 2, 5]


def test_ranking_empty_list():
    assert rank_by_overdue([], NOW) == []


def test_ranking_keeps_the_status_values():
    ranked = rank_by_overdue([CallHistory(1, 7, days_ago(14))], NOW)
    assert ranked[0].contact_id == 1
    assert ranked[0].overdue.days_since == pytest.approx(14.0)
    assert ranked[0].overdue.ratio == pytest.approx(2.0)
    assert ranked[0].overdue.is_due is True
