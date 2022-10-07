"""
Tests of git.

"""

from django.conf import settings
from evennia.commands.default.tests import BaseEvenniaCommandTest
from evennia.utils.test_resources import EvenniaTest
from evennia.contrib.utils.git_integration.git_integration import CmdGit, CmdGitEvennia
from evennia.utils.utils import list_to_string

import git
import mock
import datetime

class TestCmdGit(CmdGit):
    pass

class TestGitIntegration(EvenniaTest):
    @mock.patch("git.Repo")
    @mock.patch("git.Git")
    @mock.patch("git.Actor")
    def setUp(self, mock_git, mock_repo, mock_author):
        super().setUp()

        self.char1.msg = mock.Mock()

        p = mock_git.return_value = False
        type(mock_repo.clone_from.return_value).bare = p
        mock_repo.index.add(["mock.txt"])
        mock_git.Repo.side_effect = git.exc.InvalidGitRepositoryError

        mock_author.name = "Faux Author"
        mock_author.email = "a@email.com"

        commit_date = datetime.datetime(2021, 2, 1)

        mock_repo.index.commit(
            "Initial skeleton",
            author=mock_author,
            committer=mock_author,
            author_date=commit_date,
            commit_date=commit_date,
        )

        test_cmd_git = TestCmdGit()
        test_cmd_git.repo = mock_repo
        test_cmd_git.commit = mock_git.head.commit
        test_cmd_git.branch = mock_git.active_branch.name
        test_cmd_git.caller = self.char1
        test_cmd_git.args = "nonexistent_branch"
        self.test_cmd_git = test_cmd_git
        
    def test_git_status(self):
        time_of_commit = datetime.datetime.fromtimestamp(self.test_cmd_git.commit.committed_date)
        status_msg = '\n'.join([f"Branch: |w{self.test_cmd_git.branch}|n ({self.test_cmd_git.repo.git.rev_parse(self.test_cmd_git.commit.hexsha, short=True)}) ({time_of_commit})",
        f"By {self.test_cmd_git.commit.author.email}: {self.test_cmd_git.commit.message}"])
        self.assertEqual(status_msg, self.test_cmd_git.get_status())

    def test_git_branch(self):
        # View current branch
        remote_refs = self.test_cmd_git.repo.remote().refs
        branch_msg = f"Current branch: |w{self.test_cmd_git.branch}|n. Branches available: {list_to_string(remote_refs)}"
        self.assertEqual(branch_msg, self.test_cmd_git.get_branches())

    def test_git_checkout(self):
        # Checkout no branch
        self.test_cmd_git.checkout()
        self.char1.msg.assert_called_with("Branch 'nonexistent_branch' not available.")
        
    def test_git_pull(self):
        self.test_cmd_git.pull()
        repo = self.test_cmd_git.repo
        self.char1.msg.assert_called_with(f"You have pulled new code. Server restart initiated.|/Head now at {repo.git.rev_parse(repo.head.commit.hexsha, short=True)}.|/Author: {repo.head.commit.author.name} ({repo.head.commit.author.email})|/{repo.head.commit.message.strip()}")
    
class TestGitEvennia(BaseEvenniaCommandTest):
    def setUp(self):
        super().setUp()
        try:
            self.repo = git.Repo(settings.EVENNIA_DIR, search_parent_directories=True)
        except git.exc.InvalidGitRepositoryError:
            print("Test TestGitEvennia failed, unable to find Evennia directory.")        
        self.commit = self.repo.head.commit
        self.branch = self.repo.active_branch.name

    def test_git_evennia_status(self):
        # View current git evennia status
        time_of_commit = datetime.datetime.fromtimestamp(self.commit.committed_date)
        status_msg = '\n'.join([f"Branch: {self.branch} ({self.repo.git.rev_parse(self.commit.hexsha, short=True)}) ({time_of_commit})",
        f"By {self.commit.author.email}: {self.commit.message}"])
        self.call(
            CmdGitEvennia(),
            "status",
            status_msg
        )

    def test_git_evennia_branch(self):
        # View current branch & branches available
        remote_refs = self.repo.remote().refs
        branch_msg = f"Current branch: {self.branch}. Branches available: {list_to_string(remote_refs)}"
        self.call(
            CmdGitEvennia(),
            "branch",
            branch_msg
        )