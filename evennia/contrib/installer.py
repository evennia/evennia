from subprocess import call

import os
import logging, sys
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] [%(name)s] [%(funcName)s():%(lineno)s] %(message)s", stream=sys.stdout)

import platform

#
# -----------------------------------------------------------------------------
#

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

class Installer(object):
    
    def __init__(self):
        logger = logging.getLogger(__name__)
        logger.info("Starting %s installer..." % self.__class__.__name__)
        self.interpreter_path = sys.executable
    
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
            logger.info("Cloned Evennia repository to '%s'." % self.local_repo_path)
        except Exception as exc:
            logger.error("Could not clone Evennia repository: %s" % exc)
            return False
        
        # Install Evennia
        try:
            self.install_evennia()
            logger.info("Installed Evennia.")
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
            
        logger.info("Installation complete!")
        return True
        
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
    
    def make_workspace(self):
        """
        Creates a generic workspace folder in the user's home directory
        in which the virtualenv will be set up, Evennia's repository cloned
        and an Evennia game instance initialized.
        
        Returns:
            None
            
        """
        logger = logging.getLogger(__name__)
        
        # Figure out where to put this workspace
        self.workspace_path = os.path.join(self.identify_home(), WORKSPACE_NAME)
        logger.debug(self.workspace_path)
        
        # Check if workspace path exists
        if os.path.exists(self.workspace_path):
            raise Exception("The '%s' workspace already exists at '%s'." % (WORKSPACE_NAME, self.workspace_path))
        
        # Create it
        os.mkdir(self.workspace_path)
        
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
        
        # Figure out where we'll build this environment
        self.virtualenv_path = os.path.join(self.workspace_path, VIRTUALENV_NAME)
        logger.debug(self.virtualenv_path)
        
        # Check if virtualenv path exists
        if os.path.exists(self.virtualenv_path):
            raise Exception("Virtualenv '%s' already exists." % VIRTUALENV_NAME)
            
        # Build the command we'll run to create this environment
        args = ['virtualenv', '-p', self.interpreter_path, self.virtualenv_path]
        logger.debug(' '.join(args))
        
        # Create it
        call(args)
        
        # Figure out where the interpreter we just installed is
        self.virtual_interpreter = os.path.join(self.virtualenv_path, 'bin/python')
        logger.debug(self.virtual_interpreter)
        
        # Make sure it actually installed
        if not os.path.exists(self.virtual_interpreter):
            raise Exception("No Python binary/executable was found in '%s'." % self.virtual_interpreter)
        
    def clone_repo(self):
        """
        Downloads Evennia's source code repository using git.
        
        Returns:
            None
            
        """
        logger = logging.getLogger(__name__)
        
        # Figure out where the repository will be copied to
        self.local_repo_path = os.path.join(self.workspace_path, 'evennia')
        logger.debug(self.local_repo_path)
        
        # Build the command we'll run to perform this action
        args = ['git', 'clone', REPO_URL, self.local_repo_path]
        logger.debug(' '.join(args))
        
        # Download it
        call(args)
        
    def install_evennia(self):
        """
        Installs Evennia to the local virtual Python environment.
        
        Returns:
            None
            
        """
        logger = logging.getLogger(__name__)
        
        # Figure out where pip is installed
        self.pip_path = os.path.join(self.virtualenv_path, 'bin/pip')
        logger.debug(self.pip_path)
        
        # Check if pip exists
        if not os.path.exists(self.pip_path):
            raise Exception("No pip binary was found in '%s'." % (self.pip_path))
        
        # Build the command we'll use to install Evennia
        install_args = [self.pip_path, 'install', '-e', self.local_repo_path]
        logger.debug(' '.join(install_args))
        
        # Install it
        call(install_args)
        
    def create_game(self):
        """
        Creates an instance of an Evennia game.
        
        Returns:
            None
            
        """
        logger = logging.getLogger(__name__)
        
        # Figure out where Evennia was installed to
        self.evennia_bin_path = os.path.join(self.virtualenv_path, 'bin/evennia')
        logger.debug(self.evennia_bin_path)
        
        # Make sure Evennia exists
        if not os.path.exists(self.evennia_bin_path):
            raise Exception("No Evennia binary was found in '%s'." % self.evennia_bin_path)
        
        # Figure out where we're going to create a new game in
        self.project_path = os.path.join(self.workspace_path, PROJECT_NAME)
        logger.debug(self.project_path)
        
        # Check if something is already there
        if os.path.exists(self.project_path):
            raise Exception("A game already exists in '%s'." % self.project_path)
        
        # Build the 'create game' command
        game_args = [self.evennia_bin_path, '--init', self.project_path]
        logger.debug(' '.join(game_args))
        
        # Make it happen
        call(game_args)
        
class Windows(Installer):
    pass

class Linux(Installer):
    pass

class Apple(Installer):
    pass

if __name__ == "__main__":
    # Get platform
    env = Installer.identify_platform()
    
    if env == 'Windows':
        Windows().install()
    elif env == 'Linux':
        Linux().install()
    else:
        Apple().install()