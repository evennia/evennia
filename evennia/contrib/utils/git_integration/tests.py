"""
Tests of git.

"""

import datetime

import git
import mock

from evennia.contrib.utils.git_integration.git_integration import GitCommand
from evennia.utils.test_resources import EvenniaTest
from evennia.utils.utils import list_to_string


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

        test_cmd_git = GitCommand()
        self.repo = test_cmd_git.repo = mock_repo
        self.commit = test_cmd_git.commit = mock_git.head.commit
        self.branch = test_cmd_git.branch = mock_git.active_branch.name
        test_cmd_git.caller = self.char1
        test_cmd_git.args = "nonexistent_branch"
        self.test_cmd_git = test_cmd_git

    def test_git_status(self):
        time_of_commit = datetime.datetime.fromtimestamp(self.test_cmd_git.commit.committed_date)
        status_msg = "\n".join(
            [
                f"Branch: |w{self.test_cmd_git.branch}|n ({self.test_cmd_git.repo.git.rev_parse(self.test_cmd_git.commit.hexsha, short=True)}) ({time_of_commit})",
                f"By {self.test_cmd_git.commit.author.email}: {self.test_cmd_git.commit.message}",
            ]
        )
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
        self.char1.msg.assert_called_with(
            f"You have pulled new code. Server restart initiated.|/Head now at {self.repo.git.rev_parse(self.repo.head.commit.hexsha, short=True)}.|/Author: {self.repo.head.commit.author.name} ({self.repo.head.commit.author.email})|/{self.repo.head.commit.message.strip()}"
        )
