from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from test_voice import load


class SetupTests(unittest.TestCase):
    def test_invalid_live_configuration_is_rolled_back(self):
        setup = load('setup')
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            config = home / 'config'
            main = config / 'hypr/hyprland.lua'
            main.parent.mkdir(parents=True)
            main.write_text('-- personal\n')
            with patch.object(setup.subprocess, 'run', side_effect=[
                subprocess.CompletedProcess([], 0),
                subprocess.CompletedProcess([], 0, 'bad config'),
                subprocess.CompletedProcess([], 0),
                subprocess.CompletedProcess([], 0, '')]):
                with self.assertRaises(ValueError):
                    setup.checked_install(config, home / 'state', home / 'bin')
            self.assertEqual(main.read_text(), '-- personal\n')
            self.assertFalse((home / 'bin/omp-voice').exists())
            self.assertFalse((config / 'hypr/omp-voice-plugin.lua').exists())

    def test_shortcut_collision_is_rejected_but_own_binding_is_allowed(self):
        setup = load('setup')
        binding = {'key': 'V', 'modmask': 72, 'submap': '', 'description': 'Other app'}
        with self.assertRaises(ValueError):
            setup.check_shortcut('SUPER + ALT + V', [binding])
        binding['description'] = 'OMP Voice'
        setup.check_shortcut('SUPER + ALT + V', [binding])
        binding['description'] = 'Other app'
        binding['modmask'] = 65
        setup.check_shortcut('SUPER + ALT + V', [binding])

    def test_install_twice_preserves_user_config_and_uninstall_removes_only_managed_block(self):
        setup = load('setup')
        with tempfile.TemporaryDirectory(prefix="OMP test's home ") as directory:
            home = Path(directory)
            config = home / 'config'
            main = config / 'hypr/hyprland.lua'
            main.parent.mkdir(parents=True)
            original = '-- Personal configuration\nlocal favourite = 42\n'
            main.write_text(original)
            herdr = config / 'herdr/omp-voice.toml'
            herdr.parent.mkdir()
            herdr.write_text('# custom existing theme\n')
            setup.install(config, home / 'state', home / 'bin')
            first = main.read_text()
            setup.install(config, home / 'state', home / 'bin')
            self.assertEqual(main.read_text(), first)
            self.assertEqual(herdr.read_text(), '# custom existing theme\n')
            self.assertTrue((home / 'bin/omp-voice').stat().st_mode & 0o111)
            # Run the actual generated Lua, including window rule and keybinding.
            subprocess.run(['lua', '-e', '''
local bindings, rules, closed = {}, {}, {}
o = {window=function(match, rule) table.insert(rules, rule) end,
     bind=function(key, label, command) bindings[key] = command end}
hl = {bind=function() end, get_windows=function() return {} end}
dofile(arg[0])
assert(rules[1].float == true)
assert(rules[1].size[1] == "monitor_w * 0.60")
assert(bindings["SUPER + ALT + V"]:find(" --toggle", 1, true))
''', '--', str(config / 'hypr/omp-voice-plugin.lua')], check=True)
            setup.install(config, home / 'state', home / 'bin', uninstall=True)
            self.assertEqual(main.read_text().rstrip(), original.rstrip())
            self.assertEqual(herdr.read_text(), '# custom existing theme\n')
            self.assertTrue(list((home / 'state/omp-voice/backups').glob('*.lua')))

    def test_malformed_block_does_not_change_existing_files(self):
        setup = load('setup')
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            main = home / 'config/hypr/hyprland.lua'
            main.parent.mkdir(parents=True)
            original = '-- BEGIN migleve.omp-voice (managed)\n-- user content\n'
            main.write_text(original)
            with self.assertRaises(ValueError):
                setup.install(home / 'config', home / 'state', home / 'bin')
            self.assertEqual(main.read_text(), original)
            self.assertFalse((home / 'bin').exists())

    def test_outside_click_closes_only_visible_voice_window(self):
        template = Path(__file__).resolve().parents[1] / 'templates/outside-click.lua'
        subprocess.run(['lua', '-e', '''
local closed = {}
local voice = {class="org.omarchy.omp-voice", mapped=true, hidden=false,
               at={x=100,y=100}, size={x=200,y=100}}
local other = {class="other", mapped=true, at={x=0,y=0}, size={x=1,y=1}}
hl = {bind=function() end, get_windows=function() return {voice,other} end,
      dispatch=function(window) table.insert(closed, window) end,
      dsp={window={close=function(args) return args.window end}}}
local panel = dofile(arg[0])
panel.outside_click({x=150,y=150}); assert(#closed == 0)
panel.outside_click({x=98,y=98}); assert(#closed == 0)
panel.outside_click({x=97,y=100}); assert(#closed == 1 and closed[1] == voice)
voice.hidden = true
panel.outside_click({x=0,y=0}); assert(#closed == 1)
voice.hidden = false; voice.mapped = false
panel.outside_click({x=0,y=0}); assert(#closed == 1)
''', '--', str(template)], check=True)


if __name__ == '__main__':
    unittest.main()
