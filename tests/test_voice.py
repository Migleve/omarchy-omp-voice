import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, PROJECT / 'scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class VoiceTests(unittest.TestCase):
    def test_other_home_is_used_for_launch_and_state(self):
        # Catches hard-coded developer paths in the launcher.
        with tempfile.TemporaryDirectory(prefix='voice home ') as directory:
            with patch.dict(os.environ, {'HOME': directory, 'XDG_CONFIG_HOME': directory + '/config',
                                         'XDG_STATE_HOME': directory + '/state'}):
                voice = load('voice')
            self.assertEqual(voice.ROOT, Path(directory))
            self.assertEqual(voice.STATE, Path(directory) / 'state/omp-voice')
            self.assertEqual(voice.CONFIG, Path(directory) / 'config/herdr/omp-voice.toml')
            self.assertEqual(voice.LAUNCHER, PROJECT / 'scripts/voice.py')

    def test_attachment_failure_stops_live_voice(self):
        # Missing finally/Esc would leave the persistent server listening.
        voice = load('voice')
        calls = []
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(voice, 'STATE', Path(directory)), \
                 patch.object(voice, 'prepare', return_value='w1:p1'), \
                 patch.object(voice, 'api', side_effect=lambda *args, **kw: calls.append(args)), \
                 patch.object(voice.subprocess, 'Popen', side_effect=OSError('attach failed')), \
                 patch.object(voice.signal, 'signal'):
                with self.assertRaises(OSError):
                    voice.client()
        self.assertIn(('agent', 'send-keys', 'w1:p1', 'ctrl+l'), calls)
        self.assertEqual(calls[-1], ('agent', 'send-keys', 'w1:p1', 'esc'))

    def test_close_does_not_open_a_new_window(self):
        voice = load('voice')
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(voice, 'STATE', Path(directory)), \
                 patch.object(voice, 'run', return_value=subprocess.CompletedProcess([], 0, '[]')), \
                 patch.object(voice.subprocess, 'Popen') as popen:
                voice.toggle(action='close')
                popen.assert_not_called()

    def test_busy_agent_timeout_does_not_cancel_existing_work(self):
        voice = load('voice')
        calls = []
        def api(*args, **kwargs):
            calls.append(args)
            if args[1] == 'wait':
                raise subprocess.TimeoutExpired('herdr', 35)
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(voice, 'STATE', Path(directory)), \
                 patch.object(voice, 'prepare', return_value='w1:p1'), \
                 patch.object(voice, 'api', side_effect=api), \
                 patch.object(voice.signal, 'signal'):
                with self.assertRaises(subprocess.TimeoutExpired):
                    voice.client()
        self.assertNotIn(('agent', 'send-keys', 'w1:p1', 'esc'), calls)

    def test_cancelled_pending_launch_never_prepares_or_activates_voice(self):
        voice = load('voice')
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(voice, 'STATE', Path(directory)), \
                 patch.object(voice, 'prepare') as prepare:
                voice.client(token='cancelled')
                prepare.assert_not_called()

    def test_close_cancels_pending_launch_even_before_window_maps(self):
        voice = load('voice')
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory)
            (state / 'launch-request').write_text('pending')
            with patch.object(voice, 'STATE', state), \
                 patch.object(voice, 'run', return_value=subprocess.CompletedProcess([], 0, '[]')):
                voice.toggle(action='close')
            self.assertFalse((state / 'launch-request').exists())


if __name__ == '__main__':
    unittest.main()
