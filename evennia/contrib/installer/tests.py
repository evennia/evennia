from evennia.utils.test_resources import EvenniaTest
from mock import MagicMock, call
import mock
import tempfile

class GenericInstallerTest(EvenniaTest):
    
    home_path = tempfile.gettempdir()
    
    def setUp(self):
        from evennia.contrib import installer
        self.installer = installer.GenericInstaller(home_path=self.home_path)
        
        # Don't let actual commands be executed on filesystem
        self.installer.execute = MagicMock()
        self.installer.mkdir = MagicMock()
        
        self.workspace_name = installer.WORKSPACE_NAME
        self.repo_url = installer.REPO_URL
        
        self.commands = [
            ['virtualenv', '-p', 'python', self.workspace_name],
            ['git', 'clone', self.repo_url, 'evennia'],
            ['pip', 'install', '-e', 'evennia'],
            ['evennia', '--init', self.workspace_name]
        ]
        
    def tearDown(self):
        pass
    
    def test_install(self):
        # Test creation of workspace
        self.installer.exists = MagicMock(return_value=False)
        self.installer.install()
        
        # Confirm the command to create the workspace was called
        ex_args, kwargs = self.installer.mkdir.call_args
        self.assertTrue(self.home_path in ex_args[0])
        self.assertTrue(self.workspace_name in ex_args[0])

        # Compare outputs to expected commands and arg positions
        for cmd_num, (ex_args, kwargs) in enumerate(self.installer.execute.call_args_list[:len(self.commands)]):
            for arg_num, arg in enumerate(self.commands[cmd_num]):
                self.assertTrue(arg in ex_args[0][arg_num])