#
# Tests for the race model: start sequence lengths (3 vs 5 minute), the
# sequence length recorded on the race manager, general recall, and pickle
# recovery of the chosen sequence.
#
import unittest
import datetime
import pickle

import os
import sys
_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src')
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import model.race
from model.race import RaceManager, START_SECONDS, THREE_MINUTE_START_SECONDS
from model.utils import Signal


class StartSequenceTest(unittest.TestCase):

    def setUp(self):
        self.raceManager = RaceManager()

    def test_default_sequence_is_five_minutes(self):
        self.assertEqual(START_SECONDS, 300)
        self.assertEqual(self.raceManager.startSeconds, START_SECONDS)

    def test_three_minute_sequence_is_available(self):
        self.assertEqual(THREE_MINUTE_START_SECONDS, 180)

    def test_horn_times_per_sequence(self):
        self.assertEqual(model.race.HORN_SECONDS_BY_START[START_SECONDS],
                         (300, 240, 60, 0))
        self.assertEqual(model.race.HORN_SECONDS_BY_START[THREE_MINUTE_START_SECONDS],
                         (180, 120, 60, 0))

    def test_default_start_sequence_schedules_fleet_at_5_minutes(self):
        fleet = self.raceManager.createFleet()
        before = datetime.datetime.now()
        self.raceManager.startRaceSequence()
        expectedStart = before + datetime.timedelta(seconds=10 + START_SECONDS)
        self.assertAlmostEqual((fleet.startTime - expectedStart).total_seconds(),
                               0, delta=1)

    def test_three_minute_start_sequence_schedules_fleet(self):
        fleet = self.raceManager.createFleet()
        before = datetime.datetime.now()
        self.raceManager.startRaceSequence(THREE_MINUTE_START_SECONDS)
        self.assertEqual(self.raceManager.startSeconds, THREE_MINUTE_START_SECONDS)
        expectedStart = before + datetime.timedelta(seconds=10 + THREE_MINUTE_START_SECONDS)
        self.assertAlmostEqual((fleet.startTime - expectedStart).total_seconds(),
                               0, delta=1)

    def test_fleets_start_one_sequence_length_apart(self):
        first = self.raceManager.createFleet()
        second = self.raceManager.createFleet()
        self.raceManager.startRaceSequence(THREE_MINUTE_START_SECONDS)
        gap = (second.startTime - first.startTime).total_seconds()
        self.assertAlmostEqual(gap, THREE_MINUTE_START_SECONDS, delta=1)

    def test_next_fleet_to_start_returns_first_fleet(self):
        first = self.raceManager.createFleet()
        second = self.raceManager.createFleet()
        self.raceManager.startRaceSequence(THREE_MINUTE_START_SECONDS)
        self.assertEqual(self.raceManager.nextFleetToStart(), first)
        # once the first fleet has started, the second is next
        first.startTime = datetime.datetime.now() - datetime.timedelta(seconds=1)
        self.assertEqual(self.raceManager.nextFleetToStart(), second)


class FleetStatusTest(unittest.TestCase):

    def setUp(self):
        self.raceManager = RaceManager()

    def test_status_depends_on_sequence_length(self):
        fleet = self.raceManager.createFleet()
        # 200 seconds to go is inside the 5 minute window but outside the
        # 3 minute window
        fleet.startTime = datetime.datetime.now() + datetime.timedelta(seconds=200)
        self.assertTrue(fleet.isStarting(START_SECONDS))
        self.assertEqual(fleet.status(START_SECONDS), "Starting")
        self.assertFalse(fleet.isStarting(THREE_MINUTE_START_SECONDS))
        self.assertEqual(fleet.status(THREE_MINUTE_START_SECONDS), "Waiting to start")

    def test_pending_before_sequence(self):
        fleet = self.raceManager.createFleet()
        self.assertEqual(fleet.status(), "Pending")


class GeneralRecallTest(unittest.TestCase):

    def test_recall_of_last_fleet_restarts_after_sequence_plus_delay(self):
        raceManager = RaceManager()
        raceManager.startSeconds = THREE_MINUTE_START_SECONDS
        fleet = raceManager.createFleet()
        fleet.startTime = datetime.datetime.now() - datetime.timedelta(seconds=5)
        raceManager.generalRecall()
        secondsToGo = (fleet.startTime - datetime.datetime.now()).total_seconds()
        self.assertAlmostEqual(secondsToGo,
                               THREE_MINUTE_START_SECONDS + model.race.LAST_START_GENERAL_RECALL_DELAY,
                               delta=2)

    def test_recall_of_earlier_fleet_moves_it_to_back_of_queue(self):
        raceManager = RaceManager()
        first = raceManager.createFleet()
        second = raceManager.createFleet()
        raceManager.startRaceSequence(THREE_MINUTE_START_SECONDS)
        # let the first fleet start
        first.startTime = datetime.datetime.now() - datetime.timedelta(seconds=1)
        raceManager.generalRecall()
        self.assertEqual(raceManager.fleets[0], second)
        self.assertEqual(raceManager.fleets[-1], first)
        gap = (first.startTime - second.startTime).total_seconds()
        self.assertAlmostEqual(gap, THREE_MINUTE_START_SECONDS, delta=1)


class PersistenceTest(unittest.TestCase):

    def test_pickle_round_trip_preserves_chosen_sequence(self):
        raceManager = RaceManager()
        fleet = raceManager.createFleet("Small handicap")
        raceManager.startRaceSequence(THREE_MINUTE_START_SECONDS)

        restored = pickle.loads(pickle.dumps(raceManager))

        self.assertEqual(restored.startSeconds, THREE_MINUTE_START_SECONDS)
        self.assertEqual(restored.numberFleets(), 1)
        self.assertAlmostEqual((fleet.startTime - restored.fleets[0].startTime)
                               .total_seconds(), 0, delta=1)
        self.assertIsInstance(restored.changed, Signal)

    def test_pickle_without_start_seconds_defaults_to_five_minutes(self):
        # simulates a pickle written by a version before the configurable
        # sequence length existed
        raceManager = RaceManager()
        state = dict(raceManager.__getstate__())
        del state["startSeconds"]
        restored = RaceManager()
        restored.__setstate__(state)
        self.assertEqual(restored.startSeconds, START_SECONDS)


if __name__ == "__main__":
    unittest.main()
