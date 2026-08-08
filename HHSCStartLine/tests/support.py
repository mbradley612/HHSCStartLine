#
# Helpers shared by the tests.
#
# The model and controllers read the wall clock through datetime; freezing it
# lets the tests exercise time-based behaviour (start sequences, gun and beep
# scheduling, the lights countdown) deterministically.
#
import datetime as _real

FIXED_NOW = _real.datetime(2026, 1, 1, 12, 0, 0)


class _FrozenDatetime(_real.datetime):
    @classmethod
    def now(cls):
        return FIXED_NOW


#
# model.race uses `from datetime import datetime, timedelta`, so patching
# model.race.datetime with the frozen subclass is sufficient.
#
# controllers.controllers uses `import datetime`, so it needs a fake module
# that exposes both the frozen class and the real timedelta.
#
class _FakeDatetimeModule:
    datetime = _FrozenDatetime
    timedelta = _real.timedelta


def freeze_clock():
    import model.race
    import controllers.controllers

    model.race.datetime = _FrozenDatetime
    controllers.controllers.datetime = _FakeDatetimeModule


def reset_clock():
    import model.race
    import controllers.controllers

    model.race.datetime = _real.datetime
    controllers.controllers.datetime = _real
