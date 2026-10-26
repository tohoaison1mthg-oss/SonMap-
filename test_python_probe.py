import unittest
from unittest.mock import patch
import python_probe


class PythonProbeTests(unittest.TestCase):
    def test_python_315_is_reported_as_installed_but_incompatible(self):
        with patch.object(python_probe.sys,'version_info',(3,15,0)):
            report=python_probe.inspect_python()
        self.assertEqual(report['version'],'3.15.0')
        self.assertFalse(report['compatible'])
        self.assertIn('requires CPython 3.12',report['reason'])

    def test_32_bit_python_is_rejected_with_specific_reason(self):
        with patch.object(python_probe.sys,'version_info',(3,12,10)),patch.object(python_probe.struct,'calcsize',return_value=4):
            report=python_probe.inspect_python()
        self.assertFalse(report['compatible']);self.assertIn('64-bit',report['reason'])

    def test_missing_tkinter_is_not_misreported_as_no_python(self):
        with patch.object(python_probe.sys,'version_info',(3,12,10)),patch.object(python_probe.importlib,'import_module',side_effect=ModuleNotFoundError('No module named tkinter')):
            report=python_probe.inspect_python()
        self.assertFalse(report['compatible']);self.assertIn('tkinter',report['reason'])
        self.assertTrue(report['executable'])

    def test_supported_python_with_components_passes(self):
        with patch.object(python_probe.sys,'version_info',(3,12,10)),patch.object(python_probe.struct,'calcsize',return_value=8),patch.object(python_probe.importlib,'import_module') as load:
            report=python_probe.inspect_python()
        self.assertTrue(report['compatible'])
        self.assertEqual([call.args[0] for call in load.call_args_list],['tkinter','venv','ensurepip'])

if __name__=='__main__':unittest.main()
