#
# Tests for LightsController: which relay lights are shown as a start
# sequence counts down. These cover both the 3 and 5 minute sequences,
# including the ten second prep before the first horn (no lights), the
# per-minute countdown and the flashing in the final half minute.
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
# pyaudio and serial respectively; neither is needed for the lights logic.
pyaudio = types.ModuleType('pyaudio')
pyaudio.PyAudio = lambda: None
sys.modules['pyaudio'] = pyaudio
sys.modules['serial'] = types.ModuleType('serial')

from model.race import RaceManager, START_SECONDS, THREE_MINUTE_START_SECONDS
from controllers.controllers import LightsController
from lightsui.hardware import LIGHT_OFF, LIGHT_ON

from tests import support


class _Relay:
    def __init__(self):
        self.commands = []

    def sendRelayCommand(self, lights):
        self.commands.append(list(lights))


class _Root:
    def __init__(self):
        self._id = 0

    def after(self, *args):
        self._id += 1
        return self._id

    def after_cancel(self, scheduleId):
        pass

    def update_idletasks(self):
        pass


def lights_at(startSeconds, secondsToStart):
    #
    # Set up a race manager for the given sequence length and freeze the
    # clock, then report the lights for a fleet that is `secondsToStart`
    # away from starting.
    #
    support.freeze_clock()
    try:
        raceManager = RaceManager()
        fleet = raceManager.createFleet("A")
        raceManager.startRaceSequence(startSeconds)
        controller = LightsController(_Root(), _Relay(), raceManager)
        controller.updateTimer = None
        fleet.startTime = support.FIXED_NOW + datetime.timedelta(seconds=secondsToStart)
        return list(controller.calculateLightsDisplay())
    finally:
        support.reset_clock()


def lightsOn(lights):
    return sum(1 for light in lights if light == LIGHT_ON)


class LightsCountdownTest(unittest.TestCase):

    def test_no_lights_during_ten_second_prep(self):
        # the sequence begins before the first horn, so more time is on the
        # clock than the sequence length and nothing is shown
        for secondsToGo in (310, 305, 190, 185, 181):
            self.assertEqual(lights_at(THREE_MINUTE_START_SECONDS, secondsToGo),
                             [LIGHT_OFF] * 5,
                             "expected no lights at %d seconds to go" % secondsToGo)

    def test_five_minute_sequence_lights_count_down(self):
        cases = [
            (300, 5), (250, 5), (240, 4), (200, 4),
            (180, 3), (120, 2), (60, 1),
        ]
        for secondsToGo, expected in cases:
            lights = lights_at(START_SECONDS, secondsToGo)
            self.assertEqual(lightsOn(lights), expected,
                             "at %d seconds to go" % secondsToGo)
            # the lights fill from the first one
            self.assertEqual(lights, [LIGHT_ON] * expected + [LIGHT_OFF] * (5 - expected))

    def test_three_minute_sequence_lights_count_down(self):
        cases = [(180, 3), (150, 3), (120, 2), (90, 2), (60, 1)]
        for secondsToGo, expected in cases:
            self.assertEqual(lightsOn(lights_at(THREE_MINUTE_START_SECONDS, secondsToGo)),
                             expected, "at %d seconds to go" % secondsToGo)

    def test_three_minute_sequence_never_shows_four_lights(self):
        for secondsToGo in range(1, 320):
            self.assertLessEqual(
                lightsOn(lights_at(THREE_MINUTE_START_SECONDS, secondsToGo)),
                3, "at %d seconds to go" % secondsToGo)

    def test_lights_flash_in_final_half_minute(self):
        # 30 seconds and under: the first light alternates on and off
        self.assertEqual(lights_at(THREE_MINUTE_START_SECONDS, 15),
                         [LIGHT_ON, LIGHT_OFF, LIGHT_OFF, LIGHT_OFF, LIGHT_OFF])
        self.assertEqual(lights_at(THREE_MINUTE_START_SECONDS, 15.5),
                         [LIGHT_OFF] * 5)
        self.assertEqual(lights_at(THREE_MINUTE_START_SECONDS, 29),
                         [LIGHT_ON, LIGHT_OFF, LIGHT_OFF, LIGHT_OFF, LIGHT_OFF])
        self.assertEqual(lights_at(THREE_MINUTE_START_SECONDS, 29.5),
                         [LIGHT_OFF] * 5)

    def test_lights_out_once_started(self):
        self.assertEqual(lights_at(THREE_MINUTE_START_SECONDS, 0),
                         [LIGHT_OFF] * 5)
        self.assertEqual(lights_at(THREE_MINUTE_START_SECONDS, -5),
                         [LIGHT_OFF] * 5)


class LightsControllerUpdateTest(unittest.TestCase):

    def setUp(self):
        support.freeze_clock()
        self.addCleanup(support.reset_clock)

    def test_update_only_sends_command_when_lights_change(self):
        raceManager = RaceManager()
        fleet = raceManager.createFleet("A")
        raceManager.startRaceSequence(THREE_MINUTE_START_SECONDS)
        # bring the fleet into the countdown proper (150s to go -> 3 lights)
        fleet.startTime = support.FIXED_NOW + datetime.timedelta(seconds=150)
        relay = _Relay()
        controller = LightsController(_Root(), relay, raceManager)

        # first update goes from "nothing shown" to three lights
        controller.updateLights()
        self.assertEqual(relay.commands[-1],
                         [LIGHT_ON] * 3 + [LIGHT_OFF] * 2)
        countAfterFirstUpdate = len(relay.commands)

        # an immediate second update shows the same lights, so no command
        controller.updateLights()
        self.assertEqual(len(relay.commands), countAfterFirstUpdate)

    def test_update_turns_lights_off_when_no_fleet_to_start(self):
        raceManager = RaceManager()
        relay = _Relay()
        controller = LightsController(_Root(), relay, raceManager)
        controller.updateLights()
        self.assertEqual(relay.commands[-1], [LIGHT_OFF] * 5)


if __name__ == "__main__":
    unittest.main()
