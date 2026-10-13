"""Historical real-dialog hotkey regressions for source wiring and compiled JASS contracts."""
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import VerifyPetUIArtifact as verifier

# A deliberately small compiled-shape fixture makes mutation coverage independent
# of whether the pre-release map has already been rebuilt.
CORRECTED_JASS = '''function tdPetDialogHotkey takes integer mode, integer action returns integer
    local integer temp
    local integer temp_1
    if mode == 1 and action >= 1 and action <= 4 then
        return 48 + action
    endif
    if mode == 4 then
        if action == 10 then
            return 49
        endif
        if action == 11 then
            return 50
        endif
    endif
    if mode == 3 then
        if action == 14 then
            set temp = 49
        else
            if action == 0 then
                set temp_1 = 50
            else
                set temp_1 = 0
            endif
            set temp = temp_1
        endif
        return temp
    endif
    return 0
endfunction
function addButton takes integer lane, string label, integer action returns nothing
    local button btn
    set btn = dialog_addButton_1(TDPetUI_dialogs[lane], label, tdPetDialogHotkey(TDPetDialogSession_mode[TDPetUI_sessions[lane]], action))
endfunction
function dialog_addButton_1 takes dialog this_1, string buttonText, integer hotkey returns button
    return DialogAddButton(this_1, buttonText, hotkey)
endfunction
function showCultivation takes integer lane returns nothing
    call addButton(lane, "1 保留旧技能", 10)
    call addButton(lane, "2 替换新技能", 11)
    call addButton(lane, "1 洗练栏1", 1)
endfunction
function showReleaseConfirmation takes integer lane returns nothing
    call addButton(lane, "1 确认永久释放", 14)
    call addButton(lane, "2 取消", 0)
endfunction
'''


def source_hotkey_problems(helper, ui):
    problems = []
    contracts = [
        ('cultivate', r'if mode == TD_PET_DIALOG_CULTIVATE and action >= 1 and action <= 4\s+return 48 \+ action'),
        ('preview', r'if mode == TD_PET_DIALOG_PREVIEW\s+if action == 10\s+return 49\s+if action == 11\s+return 50'),
        ('release', r'if mode == TD_PET_DIALOG_RELEASE_CONFIRM\s+return action == 14 \? 49 : \(action == 0 \? 50 : 0\)'),
    ]
    for name, pattern in contracts:
        if re.search(pattern, helper) is None:
            problems.append(name + ' numeric hotkey mapping changed')
    if 'dialogs[lane].addButton(label, tdPetDialogHotkey(sessions[lane].mode, action))' not in ui:
        problems.append('UI buttons bypass real session-mode hotkey argument')
    for text in ['addButton(lane, "1 保留旧技能", 10)',
                 'addButton(lane, "2 替换新技能", 11)',
                 'addButton(lane, (slot + 1).toString() + " 洗练栏" + (slot + 1).toString() + " · " + tdPetQualityName(pet.qualityAt(slot)) + " " + tdPetSkillNameById(pet.skillAt(slot)), slot + 1)',
                 'addButton(lane, "1 确认永久释放", 14)',
                 'addButton(lane, "2 取消", 0)']:
        if text not in ui:
            problems.append('UI numeric button label/action changed: ' + text)
    return problems


class CompiledHotkeyContractTests(unittest.TestCase):
    def test_corrected_compiled_fixture_maps_all_contexts_and_native_arguments(self):
        verifier.verify_dialog_hotkeys(CORRECTED_JASS)

    def test_rejects_wrong_number_for_cultivate_preview_or_release(self):
        for old, new, reason in [('48 + action', '49 + action', 'mode=1 action=1'),
                                 ('if action == 10 then\n            return 49', 'if action == 10 then\n            return 50', 'mode=4 action=10'),
                                 ('set temp = 49', 'set temp = 50', 'mode=3 action=14'),
                                 ('set temp_1 = 50', 'set temp_1 = 49', 'mode=3 action=0')]:
            with self.subTest(change=old):
                with self.assertRaisesRegex(ValueError, reason):
                    verifier.verify_dialog_hotkeys(CORRECTED_JASS.replace(old, new))

    def test_rejects_preview_hotkeys_in_cultivate_context(self):
        with self.assertRaisesRegex(ValueError, 'mode=1 action=10'):
            verifier.verify_dialog_hotkeys(CORRECTED_JASS.replace('mode == 4', 'mode == 1'))

    def test_rejects_label_only_digits_with_zero_native_hotkey(self):
        bad = CORRECTED_JASS.replace('DialogAddButton(this_1, buttonText, hotkey)',
                                     'DialogAddButton(this_1, buttonText, 0)')
        with self.assertRaisesRegex(ValueError, 'real integer hotkey'):
            verifier.verify_dialog_hotkeys(bad)

    def test_rejects_ui_using_no_hotkey_overload(self):
        bad = CORRECTED_JASS.replace('dialog_addButton_1(TDPetUI_dialogs[lane], label, '
                                     'tdPetDialogHotkey(TDPetDialogSession_mode[TDPetUI_sessions[lane]], action))',
                                     'dialog_addButton(TDPetUI_dialogs[lane], label)')
        with self.assertRaisesRegex(ValueError, 'session-mode hotkey'):
            verifier.verify_dialog_hotkeys(bad)

    def test_rejects_old_preview_and_release_labels(self):
        for text in ['1 保留旧技能', '2 替换新技能', '1 确认永久释放', '2 取消']:
            with self.subTest(text=text):
                with self.assertRaisesRegex(ValueError, 'dialog lacks label'):
                    verifier.verify_dialog_hotkeys(CORRECTED_JASS.replace(text, text[2:]))


if __name__ == '__main__':
    unittest.main(verbosity=2)
