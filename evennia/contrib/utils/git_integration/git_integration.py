import datetime

import git
from django.conf import settings

from evennia import CmdSet, InterruptCommand
from evennia.commands.default.muxcommand import MuxCommand
from evennia.server.sessionhandler import SESSIONS
from evennia.utils.utils import list_to_string


class GitCommand(MuxCommand):
    """
    The shared functionality between git/git evennia
    """

    def parse(self):
        """
        Parse the arguments, set default arg to 'status' and check for existence of currently targeted repo
        """
        super().parse()

        if self.args:
            split_args = self.args.strip().split(" ", 1)
            self.action = split_args[0]
            if len(split_args) > 1:
                self.args = "".join(split_args[1:])
            else:
                self.args = ""
        else:
            self.action = "status"
            self.args = ""

        self.err_msgs = [
            "|rInvalid Git Repository|n:",
            "The {repo_type} repository is not recognized as a git directory.",
            "In order to initialize it as a git directory, you will need to access your terminal and run the following commands from within your directory:",
            "    git init",
            "    git remote add origin {remote_link}",
        ]

        try:
            self.repo = git.Repo(self.directory, search_parent_directories=True)
        except git.exc.InvalidGitRepositoryError:
            err_msg = "\n".join(self.err_msgs).format(
                repo_type=self.repo_type, remote_link=self.remote_link
            )
            self.caller.msg(err_msg)
            raise InterruptCommand

        self.commit = self.repo.head.commit

        try:
            self.branch = self.repo.active_branch.name
        except TypeError as type_err:
            self.caller.msg(type_err)
            raise InterruptCommand

    def short_sha(self, repo, hexsha):
        """
        Utility: Get the short SHA of a commit.
        """
        short_sha = repo.git.rev_parse(hexsha, short=True)
        return short_sha

    def get_status(self):
        """
        Retrieves the status of the active git repository, displaying unstaged changes/untracked files.
        """
        time_of_commit = datetime.datetime.fromtimestamp(self.commit.committed_date)
        status_msg = "\n".join(
            [
                f"Branch: |w{self.branch}|n ({self.repo.git.rev_parse(self.commit.hexsha, short=True)}) ({time_of_commit})",
                f"By {self.commit.author.email}: {self.commit.message}",
            ]
        )

        changedFiles = {item.a_path for item in self.repo.index.diff(None)}
        if changedFiles:
            status_msg += f"Unstaged/uncommitted changes:|/    |g{'|/    '.join(changedFiles)}|n|/"
        if len(self.repo.untracked_files) > 0:
            status_msg += f"Untracked files:|/    |x{'|/    '.join(self.repo.untracked_files)}|n"
        return status_msg

    def get_branches(self):
        """
        Display current and available branches.
        """
        remote_refs = self.repo.remote().refs
        branch_msg = (
            f"Current branch: |w{self.branch}|n. Branches available: {list_to_string(remote_refs)}"
        )
        return branch_msg

    def checkout(self):
        """
        Check out a specific branch.
        """
        remote_refs = self.repo.remote().refs
        to_branch = self.args.strip().removeprefix(
            "origin/"
        )  # Slightly hacky, but git tacks on the origin/

        if to_branch not in remote_refs:
            self.caller.msg(f"Branch '{to_branch}' not available.")
            return False
        elif to_branch == self.branch:
            self.caller.msg(f"Already on |w{to_branch}|n. Maybe you want <git pull>?")
            return False
        else:
            try:
                self.repo.git.checkout(to_branch)
            except git.exc.GitCommandError as err:
                self.caller.msg("Couldn't checkout {} ({})".format(to_branch, err.stderr.strip()))
                return False
            self.msg(f"Checked out |w{to_branch}|n successfully. Server restart initiated.")
            return True

    def pull(self):
        """
        Attempt to pull new code.
        """
        old_commit = self.commit
        try:
            self.repo.remotes.origin.pull()
        except git.exc.GitCommandError as err:
            self.caller.msg("Couldn't pull {} ({})".format(self.branch, err.stderr.strip()))
            return False
        if old_commit == self.repo.head.commit:
            self.caller.msg("No new code to pull, no need to reset.\n")
            return False
        else:
            self.caller.msg(
                f"You have pulled new code. Server restart initiated.|/Head now at {self.repo.git.rev_parse(self.repo.head.commit.hexsha, short=True)}.|/Author: {self.repo.head.commit.author.name} ({self.repo.head.commit.author.email})|/{self.repo.head.commit.message.strip()}"
            )
            return True

    def func(self):
        """
        Provide basic Git functionality within the game.
        """
        caller = self.caller

        if self.action == "status":
            caller.msg(self.get_status())
        elif self.action == "branch" or (self.action == "checkout" and not self.args):
            caller.msg(self.get_branches())
        elif self.action == "checkout":
            if self.checkout():
                SESSIONS.portal_restart_server()
        elif self.action == "pull":
            if self.pull():
                SESSIONS.portal_restart_server()
        else:
            caller.msg("You can only git status, git branch, git checkout, or git pull.")
            return


class CmdGitEvennia(GitCommand):
    """
    Pull the latest code from the evennia core or checkout a different branch.

    Usage:
        git evennia status - View an overview of the evennia repository status.
        git evennia branch - View available branches in evennia.
        git evennia checkout <branch> - Checkout a different branch in evennia.
        git evennia pull - Pull the latest evennia code.

    For updating your local mygame repository, the same commands are available with 'git'.

    If there are any conflicts encountered, the command will abort. The command will reload your game after pulling new code automatically, but for some changes involving persistent scripts etc, you may need to manually restart.
    """

    key = "git evennia"
    locks = "cmd:pperm(Developer)"
    help_category = "System"
    directory = settings.EVENNIA_DIR
    repo_type = "Evennia"
    remote_link = "https://github.com/evennia/evennia.git"


class CmdGit(GitCommand):
    """
    Pull the latest code from your repository or checkout a different branch.

    Usage:
        git status        - View an overview of your git repository.
        git branch        - View available branches.
        git checkout main - Checkout the main branch of your code.
        git pull          - Pull the latest code from your current branch.

    For updating evennia code, the same commands are available with 'git evennia'.

    If there are any conflicts encountered, the command will abort. The command will reload your game after pulling new code automatically, but for changes involving persistent scripts etc, you may need to manually restart.
    """

    key = "git"
    locks = "cmd:pperm(Developer)"
    help_category = "System"
    directory = settings.GAME_DIR
    repo_type = "game"
    remote_link = "[your remote link]"


# CmdSet for easily install all commands
class GitCmdSet(CmdSet):
    """
    The git command.
    """

    def at_cmdset_creation(self):
        self.add(CmdGit)
        self.add(CmdGitEvennia)
