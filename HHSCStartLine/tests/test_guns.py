#
# Tests for GunController: the horns (and their preceding warning beeps) that
# are scheduled for each start sequence length, and the gun timing maths.
#
import unittest
import types
import sys
import datetime

import os
_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src')
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

# controllers imports screenui.audio and lightsui.hardware which import
# pyaudio and serial respectively; neither is needed for the gun logic.
pyaudio = types.ModuleType('pyaudio')
pyaudio.PyAudio = lambda: None
sys.modules['pyaudio'] = pyaudio
sys.modules['serial'] = types.ModuleType('serial')

from model.race import RaceManager, START_SECONDS, THREE_MINUTE_START_SECONDS
from controllers.controllers import GunController

from tests import support


class _Root:
    def __init__(self):
        self.afterCalls = []
        self._id = 0

    def after(self, delayMillis, func):
        self._id += 1
        self.afterCalls.append((delayMillis, func))
        return self._id

    def after_cancel(self, scheduleId):
        pass


class _Audio:
    def __init__(self):
        self.clips = []

    def queueClip(self, clipName):
        self.clips.append(clipName)


class GunScheduleTest(unittest.TestCase):

    def setUp(self):
        support.freeze_clock()
        self.addCleanup(support.reset_clock)

    def scheduleFor(self, sequenceSeconds):
        raceManager = RaceManager()
        raceManager.createFleet("A")
        raceManager.startRaceSequence(sequenceSeconds)
        root = _Root()
        controller = GunController(root, _Audio(), raceManager)
        controller.scheduleGunsForFutureFleetStarts()
        return root, controller

    def assertHornsAt(self, root, controller, gunMillis):
        gunDelays = [delay for delay, func in root.afterCalls
                     if func == controller.fireStartGun]
        self.assertEqual(sorted(gunDelays), sorted(gunMillis))
        # every horn is preceded by ten one-second warning beeps
        beepDelays = [delay for delay, func in root.afterCalls
                      if func == controller.soundWarning]
        self.assertEqual(len(beepDelays), 10 * len(gunMillis))
        for millis in gunMillis:
            expectedBeeps = range(millis - 10000, millis, 1000)
            for beep in expectedBeeps:
                self.assertIn(beep, beepDelays)

    def test_three_minute_sequence_horns(self):
        # the fleet starts ten seconds after the sequence starts, so the
        # horns at 180/120/60/0 seconds before start fall at 10/70/130/190
        # seconds
        root, controller = self.scheduleFor(THREE_MINUTE_START_SECONDS)
        self.assertHornsAt(root, controller,
                           [10000, 70000, 130000, 190000])

    def test_five_minute_sequence_horns(self):
        root, controller = self.scheduleFor(START_SECONDS)
        self.assertHornsAt(root, controller,
                           [10000, 70000, 250000, 310000])


class GunTimingTest(unittest.TestCase):

    def setUp(self):
        support.freeze_clock()
        self.addCleanup(support.reset_clock)

    def test_calculate_gun_millis(self):
        raceManager = RaceManager()
        fleet = raceManager.createFleet("A")
        # as if a 3 minute sequence started ten seconds ago
        fleet.startTime = support.FIXED_NOW + datetime.timedelta(seconds=190)
        controller = GunController(_Root(), _Audio(), raceManager)
        self.assertEqual(controller.calculateGunMillisForFleetStart(fleet, 180), 10000)
        self.assertEqual(controller.calculateGunMillisForFleetStart(fleet, 60), 130000)
        self.assertEqual(controller.calculateGunMillisForFleetStart(fleet, 0), 190000)

    def test_warning_beeps_precede_gun(self):
        root = _Root()
        controller = GunController(root, _Audio(), RaceManager())
        controller.scheduleWarningBeeps(10000)
        beepDelays = [delay for delay, func in root.afterCalls
                      if func == controller.soundWarning]
        self.assertEqual(beepDelays, list(range(0, 10000, 1000)))

    def test_start_gun_scheduled_at_requested_time(self):
        root = _Root()
        controller = GunController(root, _Audio(), RaceManager())
        controller.scheduleStartGun(12345)
        gunDelays = [delay for delay, func in root.afterCalls
                     if func == controller.fireStartGun]
        self.assertEqual(gunDelays, [12345])


if __name__ == "__main__":
    unittest.main()
