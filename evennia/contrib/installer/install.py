from subprocess import call

import os
import logging, sys
logging.basicConfig(level=logging.DEBUG, format="[%(asctime)s] [%(levelname)s] [%(name)s] [%(funcName)s():%(lineno)s] %(message)s", stream=sys.stdout)

import platform

#
# -----------------------------------------------------------------------------
#

# The name of your intended game.
PROJECT_NAME = 'demo'

#
# -----------------------------------------------------------------------------
#

WORKSPACE_NAME = 'mud_devel'
VIRTUALENV_NAME = PROJECT_NAME.upper()[:5]
REPO_URL = 'https://github.com/evennia/evennia.git'

#
# -----------------------------------------------------------------------------
#

class GenericInstaller(object):
    
    def __init__(self, **kwargs):
        logger = logging.getLogger(__name__)
        logger.info("Starting %s..." % self.__class__.__name__)
        logger.info("Assembling list of target resources...")
        
        # Where is the current interpreter?
        self.interpreter_path = kwargs.get('interpreter_path', self.identify_interpreter())
        logger.info("Python Interpreter: %s" % self.interpreter_path)
        
        # What is the current user's home directory?
        self.home_path = kwargs.get('home_path', self.identify_home())
        logger.info("User Home: %s" % self.home_path)
        
        # Figure out where to build the workspace
        self.workspace_path = kwargs.get('workspace_path', self.join(self.home_path, WORKSPACE_NAME))
        logger.info('Workspace: %s' % self.workspace_path)
        assert not self.exists(self.workspace_path), "Workspace '%s' already exists!" % self.workspace_path
        
        # Figure out where to build the virtualenv
        self.virtualenv_path = kwargs.get('virtualenv_path', self.join(self.workspace_path, VIRTUALENV_NAME))
        logger.info('Virtualenv: %s' % self.virtualenv_path)
        assert not self.exists(self.virtualenv_path), "Virtualenv '%s' already exists!" % self.virtualenv_path
        
        # Figure out where the virtual interpreter will be
        self.virtualenv_interpreter_path = kwargs.get('virtualenv_interpreter_path', self.join(self.virtualenv_path, 'bin/python'))
        logger.info('Virtual Python Interpreter: %s' % self.virtualenv_interpreter_path)
        assert not self.exists(self.virtualenv_path), "Virtualenv Interpreter '%s' already exists!" % self.virtualenv_interpreter_path
        
        # Figure out where the repository will be copied to
        self.evennia_repo_path = kwargs.get('evennia_repo_path', self.join(self.workspace_path, 'evennia'))
        logger.info('Evennia Repo: %s' % self.evennia_repo_path)
        assert not self.exists(self.evennia_repo_path), "Evennia repository at '%s' already exists!" % self.evennia_repo_path
        
        # Figure out where pip will be installed
        self.pip_bin_path = kwargs.get('pip_bin_path', self.join(self.virtualenv_path, 'bin/pip'))
        logger.info('Pip Executable: %s' % self.pip_bin_path)
        assert not self.exists(self.pip_bin_path), "Pip '%s' already installed!" % self.pip_bin_path
        
        # Figure out where Evennia was installed to
        self.evennia_bin_path = kwargs.get('evennia_bin_path', self.join(self.virtualenv_path, 'bin/evennia'))
        logger.info('Evennia Executable: %s' % self.evennia_bin_path)
        assert not self.exists(self.evennia_bin_path), "Evennia '%s' already installed!" % self.evennia_bin_path
        
         # Figure out where the new game will be initialized
        self.project_path = kwargs.get('project_path', self.join(self.workspace_path, PROJECT_NAME))
        logger.info('%s Instance: %s' % (PROJECT_NAME.title(), self.project_path))
        assert not self.exists(self.project_path), "Project '%s' already exists!" % self.project_path
        
    @classmethod
    def identify_platform(cls):
        """
        Returns:
            platform (str): A string identifying the platform 
                in use (Windows, Linux, etc.)
        
        """
        return platform.system()
        
    @classmethod
    def identify_home(cls):
        """
        Returns:
            home_path (str): The path to the current user's home directory
                or functional equivalent.
                
        """
        return os.path.expanduser("~")
        
    @classmethod
    def identify_interpreter(cls):
        """
        Returns:
            path (str): Path to the currently running Python interpreter.
            
        """
        return sys.executable
    
    @classmethod
    def exists(cls, path):
        """
        Checks if the given path exists on the filesystem.
        
        """
        return os.path.exists(path)
        
    @classmethod
    def execute(cls, args=[]):
        """
        Executes a command.
        
        """
        return call(args)
        
    @classmethod
    def mkdir(cls, path):
        """
        Creates a directory.
        
        """
        return os.mkdir(path)
        
    @classmethod
    def chdir(cls, path):
        """
        Changes directories from the current working one to something else.
        
        """
        return os.chdir(path)
        
    @classmethod
    def join(cls, *fragments):
        """
        Joins two paths per filesystem rules.
        
        """
        return os.path.join(*fragments)
        
    def install(self):
        """
        Main execution point.
        
        """
        logger = logging.getLogger(__name__)
        
        # Create a working folder to install everything in
        try:
            self.make_workspace()
            logger.info("Created workspace '%s'." % self.workspace_path)
        except Exception as exc:
            logger.error("Could not create workspace: %s" % exc)
            return False
        
        # Create a virtual environment in the workspace to install local versions
        # of the Python/Evennia libraries
        try:
            self.create_virtualenv()
            logger.info("Created virtual environment '%s' in '%s'." % (VIRTUALENV_NAME, self.virtualenv_path))
        except Exception as exc:
            logger.error("Could not create virtual environment: %s" % exc)
            return False
        
        # Download the Evennia source code
        try:
            self.clone_repo()
            logger.info("Cloned Evennia repository to '%s'." % self.evennia_repo_path)
        except Exception as exc:
            logger.error("Could not clone Evennia repository: %s" % exc)
            return False
        
        # Install Evennia
        try:
            self.install_evennia()
            logger.info("Installed Evennia to virtual Python environment.")
        except Exception as exc:
            logger.error("Could not install Evennia: %s" % exc)
            return False
        
        # Create an instance of a game
        try:
            self.create_game()
            logger.info("Created new game instance in '%s'." % self.project_path)
        except Exception as exc:
            logger.error("Could not create a new game instance: %s" % exc)
            return False
            
        # Perform migration
        try:
            self.migrate_db()
            logger.info("Performed database initialization.")
        except Exception as exc:
            logger.error("Could not migrate database: %s" % exc)
            return False
            
        logger.info("Installation complete!")
        return True
        
    def make_workspace(self):
        """
        Creates a generic workspace folder in the user's home directory
        in which the virtualenv will be set up, Evennia's repository cloned
        and an Evennia game instance initialized.
        
        Returns:
            None
            
        """
        # Create it
        self.mkdir(self.workspace_path)
        
    def create_virtualenv(self):
        """
        Creates a Python virtual environment containing local copies of all the
        system libraries.
        
        The reason for this is twofold: one, it's cleaner and safer than
        installing Evennia system-wide with root/admin privilege, and two, it's
        easier to erase everything and start over if the need arises when
        everything is compartmentalized in this manner.
        
        Returns:
            None
            
        """
        logger = logging.getLogger(__name__)
        
        # Build the command we'll run to create this environment
        args = ['virtualenv', '-p', self.interpreter_path, self.virtualenv_path]
        logger.debug(' '.join(args))
        
        # Create it
        self.execute(args)
        
    def clone_repo(self):
        """
        Downloads Evennia's source code repository using git.
        
        Returns:
            None
            
        """
        logger = logging.getLogger(__name__)
        
        # Build the command we'll run to perform this action
        args = ['git', 'clone', REPO_URL, self.evennia_repo_path]
        logger.debug(' '.join(args))
        
        # Download it
        self.execute(args)
        
    def install_evennia(self):
        """
        Installs Evennia to the local virtual Python environment.
        
        Returns:
            None
            
        """
        logger = logging.getLogger(__name__)
        
        # Build the command we'll use to install Evennia
        install_args = [self.pip_bin_path, 'install', '-e', self.evennia_repo_path]
        logger.debug(' '.join(install_args))
        
        # Install it
        self.execute(install_args)
        
    def create_game(self):
        """
        Creates an instance of an Evennia game.
        
        Returns:
            None
            
        """
        logger = logging.getLogger(__name__)
        
        # Build the 'create game' command
        game_args = [self.evennia_bin_path, '--init', self.project_path]
        logger.debug(' '.join(game_args))
        
        # Make it happen
        self.execute(game_args)
        
    def migrate_db(self):
        """
        Initializes the database for the new game.
        
        Returns:
            None
            
        """
        logger = logging.getLogger(__name__)
        
        # Build the migration command
        # This requires changing to the game directory 
        self.chdir(self.project_path)

        # ...and calling 'evennia migrate' from there
        args = [self.evennia_bin_path, 'migrate']
        logger.debug(' '.join(args))
        
        # Make it happen
        self.execute(args)
        
class WindowsInstaller(GenericInstaller):
    pass

class LinuxInstaller(GenericInstaller):
    pass

class AppleInstaller(GenericInstaller):
    pass

if __name__ == "__main__":
    # Get platform
    env = GenericInstaller.identify_platform()
    
    if env == 'Windows':
        WindowsInstaller().install()
    elif env == 'Linux':
        LinuxInstaller().install()
    else:
        AppleInstaller().install()