#
# Tests for the audio clips used by the app, notably the shortened finish
# horn (issue #45). The clip is a stereo wav with the sound on the left
# channel (outdoor speakers) and silence on the right.
#
import unittest
import types
import sys
import os
import array

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src')
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

# screenui.audio imports pyaudio at module level; only AudioClip is tested
# here, which does not touch the audio device.
pyaudio = types.ModuleType('pyaudio')
pyaudio.PyAudio = lambda: None
sys.modules['pyaudio'] = pyaudio

from screenui.audio import AudioClip

MEDIA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     'media')


class AudioClipTest(unittest.TestCase):

    def setUp(self):
        self.clip = AudioClip(os.path.join(MEDIA, '0.5-Second-Horn-left.wav'))

    def test_finish_horn_duration_is_half_a_second(self):
        self.assertAlmostEqual(self.clip.wavDuration, 500, delta=100)

    def test_finish_horn_is_16_bit_stereo(self):
        self.assertEqual(self.clip.wav.getsampwidth(), 2)
        self.assertEqual(self.clip.wav.getnchannels(), 2)

    def test_finish_horn_sound_is_on_left_channel_only(self):
        self.clip.openWav()
        frames = self.clip.wav.readframes(self.clip.wav.getnframes())
        samples = array.array('h', frames)  # interleaved left, right
        left = samples[0::2]
        right = samples[1::2]
        self.assertGreater(max(abs(sample) for sample in left), 5000)
        self.assertLess(max(abs(sample) for sample in right), 200)


if __name__ == "__main__":
    unittest.main()
