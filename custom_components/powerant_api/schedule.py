"""PowerAnt scheduling calculations."""

from __future__ import annotations

from datetime import datetime


def _apply_cheapest_time(
    entries: list[dict],
    cheapest_hours: float,
    period_minutes: int,
) -> None:
    """Apply PowerAnt cheapest time scheduling."""

    for entry in entries:
        entry["is_on"] = False

    total_intervals = len(entries)
    cheapest_hours = max(0, float(cheapest_hours or 0))

    if not total_intervals or cheapest_hours <= 0:
        return

    intervals_per_hour = 60 / period_minutes

    wanted_intervals = min(
        total_intervals,
        round(cheapest_hours * intervals_per_hour),
    )

    if wanted_intervals <= 0:
        return

    candidates = sorted(
        (entry for entry in entries if entry["rule"] != "ON"),
        key=lambda entry: (
            entry["effective"],
            entry["timestamp"],
        ),
    )

    for entry in candidates[:wanted_intervals]:
        entry["is_on"] = True


def _apply_time_slots(
    entries: list[dict],
    cheapest_hours: float,
    time_slots: int,
    period_minutes: int,
) -> None:
    """Apply PowerAnt time slots scheduling."""

    for entry in entries:
        entry["is_on"] = False

    total_intervals = len(entries)
    cheapest_hours = max(
        0,
        float(cheapest_hours or 0),
    )
    raw_slots = int(time_slots or 0)

    if (
        not total_intervals
        or not raw_slots
        or cheapest_hours <= 0
    ):
        return

    num_slots = max(
        1,
        min(raw_slots, 24),
    )

    intervals_per_hour = 60 / period_minutes

    wanted_intervals = min(
        total_intervals,
        round(
            cheapest_hours * intervals_per_hour
        ),
    )

    if wanted_intervals <= 0:
        return

    #
    # 15-minute prices
    #
    # Divide the requested periods as evenly as possible
    # between the slots. Any remainder starts from Slot 1.
    #
    if period_minutes == 15:

        base_slot_size = (
            total_intervals // num_slots
        )

        extra_periods = (
            total_intervals % num_slots
        )

        base_wanted = (
            wanted_intervals // num_slots
        )

        extra_wanted = (
            wanted_intervals % num_slots
        )

        start_index = 0

        for slot_index in range(num_slots):

            slot_size = base_slot_size

            if slot_index < extra_periods:
                slot_size += 1

            end_index = (
                start_index + slot_size
            )

            slot_entries = entries[
                start_index:end_index
            ]

            slot_wanted = base_wanted

            if slot_index < extra_wanted:
                slot_wanted += 1

            candidates = sorted(
                (
                    entry
                    for entry in slot_entries
                    if entry["rule"] != "ON"
                ),
                key=lambda entry: (
                    entry["effective"],
                    entry["timestamp"],
                ),
            )

            for entry in candidates[:slot_wanted]:
                entry["is_on"] = True

            start_index = end_index

        return

    #
    # 60-minute prices
    #
    # Selection happens in rounds:
    #
    #   Round 1 -> cheapest hour from every slot
    #   Round 2 -> second cheapest hour from every slot
    #   ...
    #
    # Within each round the candidates are compared by price.
    #
    if period_minutes == 60:

        slot_candidates = {}

        for slot_number in range(num_slots):

            candidates = []

            for entry in entries:

                timestamp = entry["timestamp"]
                hour = int(timestamp[8:10])

                slot_index = min(
                    int(
                        hour * num_slots / 24
                    ),
                    num_slots - 1,
                )

                if (
                    slot_index == slot_number
                    and entry["rule"] != "ON"
                ):
                    candidates.append(entry)

            candidates.sort(
                key=lambda entry: (
                    entry["effective"],
                    entry["timestamp"],
                )
            )

            slot_candidates[
                slot_number
            ] = candidates

        remaining = wanted_intervals
        round_index = 0

        while remaining > 0:

            round_candidates = []

            for candidates in slot_candidates.values():

                if round_index < len(candidates):

                    entry = candidates[
                        round_index
                    ]

                    round_candidates.append(entry)

            if not round_candidates:
                break

            round_candidates.sort(
                key=lambda entry: (
                    entry["effective"],
                    entry["timestamp"],
                )
            )

            for entry in round_candidates:

                if remaining <= 0:
                    break

                entry["is_on"] = True
                remaining -= 1

            round_index += 1

        return


def _calculate_status(
    entries: list[dict],
    mode: str,
    cheapest_hours: float,
    price_trigger: float,
    time_slots: int,
    period_minutes: int,
) -> None:
    """Calculate PowerAnt control state for all price periods."""

    mode = str(mode or "").upper()

    #
    # First calculate the normal scheduling logic.
    #
    if mode == "ON":

        for entry in entries:
            entry["is_on"] = True

    elif mode == "OFF":

        for entry in entries:
            entry["is_on"] = False

    elif mode == "TIME":

        _apply_cheapest_time(
            entries,
            cheapest_hours,
            period_minutes,
        )

    elif mode == "TRIGGER":

        for entry in entries:
            entry["is_on"] = (
                entry["effective"] < price_trigger
            )

    elif mode == "TIME_AND_TRIGGER":

        _apply_cheapest_time(
            entries,
            cheapest_hours,
            period_minutes,
        )

        for entry in entries:
            entry["is_on"] = (
                entry["is_on"]
                and entry["effective"] < price_trigger
            )

    elif mode == "TIME_OR_TRIGGER":

        _apply_cheapest_time(
            entries,
            cheapest_hours,
            period_minutes,
        )

        for entry in entries:
            entry["is_on"] = (
                entry["is_on"]
                or entry["effective"] < price_trigger
            )

    elif mode == "REVERSE_OR":

        _apply_cheapest_time(
            entries,
            cheapest_hours,
            period_minutes,
        )

        for entry in entries:
            entry["is_on"] = (
                entry["is_on"]
                or entry["effective"] < price_trigger
            )

    elif mode == "TIME_SLOTS":

        _apply_time_slots(
            entries,
            cheapest_hours,
            time_slots,
            period_minutes,
        )

    else:

        for entry in entries:
            entry["is_on"] = False

    #
    # Apply tariff ON/OFF after normal scheduling.
    #
    # ON  -> force logical state ON
    # OFF -> force logical state OFF
    #
    for entry in entries:

        if entry["rule"] == "ON":
            entry["is_on"] = True

        elif entry["rule"] == "OFF":
            entry["is_on"] = False

    #
    # Reverse mode reverses the final relay output.
    #
    if mode == "REVERSE_OR":

        for entry in entries:
            entry["is_on"] = not entry["is_on"]


def _find_next_change(
    entries: list[dict],
    tomorrow_entries: list[dict],
    current_index: int,
    timestamp_format: str,
) -> dict | None:
    """Find the next ON/OFF state change."""

    current = entries[current_index]

    future_entries = (
        entries[current_index + 1:]
        + tomorrow_entries
    )

    for entry in future_entries:

        if entry["is_on"] != current["is_on"]:

            change = datetime.strptime(
                entry["timestamp"],
                timestamp_format,
            )

            return {
                "time": change.strftime("%H:%M"),
                "state": entry["is_on"],
            }

    return None
