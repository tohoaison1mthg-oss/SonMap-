import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from topology_workflow import focus_issue,clear_error_markers,digest,issue_point


class ErrorNavigationTests(unittest.TestCase):
    def test_zoom_centres_on_dangling_endpoint_not_midpoint_of_whole_edge(self):
        project={'source':{'path':'source.dgn'},'model':'Default','options':{'metres_per_unit':1},'parcels':[]}
        issue={'code':'DANGLE','point':[5,7],'points':[[5,7],[500,700]]}
        with patch('cad_bridge.request') as focus:
            focus_issue(project,issue,.5)
        self.assertEqual(focus.call_args.kwargs['x'],5)
        self.assertEqual(focus.call_args.kwargs['y'],7)
        self.assertEqual(focus.call_args.kwargs['span'],1.5)
        self.assertEqual(focus.call_args.kwargs['model'],'Default')

    def test_selective_clear_uses_issue_anchor_and_current_saved_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/'source.dgn';source.write_bytes(b'before manual edit')
            project={'source':{'path':str(source),'sha256':'old-analysis'},'model':'Default','parcels':[]}
            issue={'point':[5,7],'points':[[500,700],[6,8]]}
            seen=[]
            def execute(script,*args):
                action=args[args.index('-Action')+1]
                if action=='SaveActive':
                    self.assertIn('-ModelName',args)
                    source.write_bytes(b'saved manual edit')
                elif action=='ClearErrors':
                    plan=json.loads(Path(args[args.index('-InputPath')+1]).read_text())
                    seen.append(plan)
                    self.assertEqual(plan['marker_point'],[5,7])
                    self.assertEqual(plan['model'],'Default')
                    self.assertEqual(plan['source']['sha256'],digest(source))
                    self.assertEqual(Path(plan['direct_backup']).read_bytes(),b'saved manual edit')
            with patch('topology_workflow.powershell',side_effect=execute):
                clear_error_markers(source,project,issue)
            self.assertFalse(Path(seen[0]['direct_backup']).exists())
            self.assertEqual(source.read_bytes(),b'saved manual edit')

    def test_missing_anchor_and_changed_source_stop_before_save(self):
        project={'source':{'path':'other.dgn'},'model':'Default','parcels':[]}
        with patch('topology_workflow.powershell') as execute:
            with self.assertRaises(ValueError):clear_error_markers('source.dgn',project,{'code':'NO_PARCELS'})
            execute.assert_not_called()
        self.assertEqual(issue_point({'parcels':[{'ID':4,'centre':[1,2]}]}, {'parcel':4}),[1,2])
