"""Forward-looking abstraction for the production vision described in the
spec (observe user activity -> detect repetitive workflows -> suggest
automation). Not wired into anything for the MVP -- start()/stop() are no-ops
and get_events() returns an empty list. Do not build this out further until
the DEMO_MODE loop above is solid; this exists only so the shape is in place.
"""


class ActivityObserver:
    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def get_events(self) -> list[dict]:
        return []
