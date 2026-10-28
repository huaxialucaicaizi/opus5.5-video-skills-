#!/usr/bin/env python3
"""Unit tests for the validators: each planted defect must trip exactly the check that names it."""
import copy, json, shutil, sys, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from common import REPO, reading_time, load_json  # noqa: E402
import validate_spec, layout_check  # noqa: E402

EX = REPO / 'examples/ai-explainer-15s'
STYLE = load_json(REPO / 'templates/visual-style/style.default.json')

def status(checks, cid):
    return next(c['status'] for c in checks if c['id'] == cid)

class Project:
    """Temp copy of the example project, with the style path made absolute."""
    def __init__(self):
        self.dir = Path(tempfile.mkdtemp(prefix='avs-test-'))
        self.sb = load_json(EX / 'storyboard.json'); self.task = load_json(EX / 'task.json')
        self.sb['style'] = self.task['style'] = str(REPO / 'templates/visual-style/style.default.json')
    def scene(self, sid): return next(s for s in self.sb['scenes'] if s['id'] == sid)
    def write(self):
        (self.dir / 'storyboard.json').write_text(json.dumps(self.sb, ensure_ascii=False))
        (self.dir / 'task.json').write_text(json.dumps(self.task, ensure_ascii=False))
        return self.dir
    def close(self): shutil.rmtree(self.dir, ignore_errors=True)

class SpecTests(unittest.TestCase):
    def setUp(self): self.p = Project()
    def tearDown(self): self.p.close()
    def run_spec(self): return validate_spec.run(self.p.write())

    def test_example_passes(self):
        r = self.run_spec()
        self.assertEqual([c['id'] for c in r if c['status'] == 'fail'], [])

    def test_gap_between_scenes(self):
        self.p.scene('s3_probs')['start'] = 5.8
        self.assertEqual(status(self.run_spec(), 'S1.contiguous'), 'fail')

    def test_duration_mismatch_with_task(self):
        self.p.task['duration_s'] = 16
        self.assertEqual(status(self.run_spec(), 'S1.match'), 'fail')

    def test_short_read(self):
        r0 = self.p.scene('s2_tokens')['reads'][0]; r0['end'] = r0['start'] + 0.3
        self.assertEqual(status(self.run_spec(), 'S2.reads'), 'fail')

    def test_overlapping_reads(self):
        rd = self.p.scene('s3_probs')['reads']; rd[1]['start'] = rd[0]['start'] + 0.2
        self.assertEqual(status(self.run_spec(), 'S2.reads'), 'fail')

    def test_text_too_short_to_read(self):
        self.p.scene('s4_loop')['on_screen_text'][-1].update(start=12.0, end=12.5)
        self.assertEqual(status(self.run_spec(), 'S3.reading'), 'fail')

    def test_off_beat_cut_is_only_a_warning(self):
        self.p.scene('s2_tokens')['end'] = 5.6; self.p.scene('s3_probs')['start'] = 5.6
        self.assertEqual(status(self.run_spec(), 'S4.beats'), 'warn')

    def test_hard_ending(self):
        self.p.scene('s5_takeaway')['transition_out'] = {'type': 'none'}
        self.assertEqual(status(self.run_spec(), 'S5.transitions'), 'fail')

    def test_unregistered_component(self):
        self.p.scene('s3_probs')['component'] = 'fancy-bars'
        self.assertEqual(status(self.run_spec(), 'S6.components'), 'fail')

    def test_unknown_licence(self):
        self.p.task['assets'] = [{'id': 'x', 'path': 'x.mp3', 'author': 'someone', 'license': 'unknown', 'commercial_use': False}]
        self.assertEqual(status(self.run_spec(), 'L1.licences'), 'fail')

    def test_portrait_style_on_landscape_frame(self):
        self.p.sb.update(width=1920, height=1080); self.p.task['format'].update(width=1920, height=1080)
        self.assertEqual(status(self.run_spec(), 'S7.style_fit'), 'fail')
    def test_landscape_style_fits_landscape(self):
        self.p.sb.update(width=1920, height=1080); self.p.task['format'].update(width=1920, height=1080)
        self.p.sb['style'] = str(REPO / 'templates/visual-style/style.landscape.json')
        self.assertEqual(status(self.run_spec(), 'S7.style_fit'), 'pass')
    def test_schema_violation(self):
        del self.p.scene('s1_hook')['event']
        self.assertEqual(status(self.run_spec(), 'S1.schema'), 'fail')

class ReadingTimeTests(unittest.TestCase):
    def test_min_hold(self): self.assertAlmostEqual(reading_time('好', STYLE), STYLE['readability']['min_text_hold_s'])
    def test_cjk_rate(self): self.assertAlmostEqual(reading_time('一' * 12, STYLE), 12 / STYLE['readability']['zh_chars_per_s'])
    def test_mixed(self): self.assertGreater(reading_time('把句子切成 token 再打分', STYLE), reading_time('把句子切成再打分', STYLE))

class LayoutTests(unittest.TestCase):
    def setUp(self): self.p = Project()
    def tearDown(self): self.p.close()
    def layout(self, boxes, transition=False):
        d = self.p.write(); (d / 'out').mkdir(exist_ok=True)
        L = {'width': 1080, 'height': 1920, 'step': 0.1, 'samples': [{'t': 1.0, 'scene': 's1_hook', 'transition': transition, 'boxes': boxes}]}
        (d / 'out/layout.json').write_text(json.dumps(L))
        return layout_check.run(d)
    box = staticmethod(lambda i, x, y, w=200, h=60, px=60, a=1: {'id': i, 'text': i, 'role': 'body', 'scene': 's1_hook', 'x': x, 'y': y, 'w': w, 'h': h, 'px': px, 'alpha': a})

    def test_clean(self):
        r = self.layout([self.box('a', 100, 400), self.box('b', 100, 600)])
        self.assertEqual([c['status'] for c in r if c['id'] != 'V4.reserved'], ['pass', 'pass', 'pass', 'pass'])
    def test_outside_safe_area(self): self.assertEqual(status(self.layout([self.box('a', 100, 1600)]), 'V1.safe_area'), 'fail')
    def test_transition_samples_are_not_judged_for_safe_area(self): self.assertEqual(status(self.layout([self.box('a', 100, 1600)], transition=True), 'V1.safe_area'), 'pass')
    def test_faint_text_ignored(self): self.assertEqual(status(self.layout([self.box('a', 100, 1600, a=0.2)]), 'V1.safe_area'), 'pass')
    def test_small_font(self): self.assertEqual(status(self.layout([self.box('a', 100, 400, px=20)]), 'V2.min_px'), 'fail')
    def test_overlap(self): self.assertEqual(status(self.layout([self.box('a', 100, 400), self.box('b', 150, 420)]), 'V3.overlap'), 'fail')
    def test_text_spills_out_of_container(self):
        c = {'id': 'a:box', 'text': '', 'role': 'container', 'kind': 'container', 'scene': 's1_hook', 'x': 100, 'y': 400, 'w': 150, 'h': 80, 'px': 0, 'alpha': 1}
        t = {**self.box('a', 110, 410, w=220, h=60), 'parent': 'a:box'}
        self.assertEqual(status(self.layout([c, t]), 'V5.contained'), 'fail')
    def test_text_inside_container(self):
        c = {'id': 'a:box', 'text': '', 'role': 'container', 'kind': 'container', 'scene': 's1_hook', 'x': 100, 'y': 400, 'w': 300, 'h': 80, 'px': 0, 'alpha': 1}
        t = {**self.box('a', 110, 410, w=200, h=60), 'parent': 'a:box'}
        r = self.layout([c, t])
        self.assertEqual(status(r, 'V5.contained'), 'pass'); self.assertEqual(status(r, 'V2.min_px'), 'pass')
    def test_reserved_region(self):
        self.p.sb['reserved_regions'] = [{'x': 600, 'y': 900, 'w': 300, 'h': 300, 'label': 'pip'}]
        self.assertEqual(status(self.layout([self.box('a', 650, 950)]), 'V4.reserved'), 'fail')

if __name__ == '__main__':
    unittest.main(verbosity=1)
