from unittest.mock import MagicMock, Mock, patch

from evennia.comms.models import TempMsg
from evennia.utils import create
from evennia.utils.test_resources import EvenniaCommandTest

from . import menu, reports


class _MockQuerySet(list):
    def order_by(self, *args, **kwargs):
        return self

    def exclude(self, *args, **kwargs):
        return self

    def filter(self, *args, **kwargs):
        return self


def _mock_pre(cmdobj):
    """helper to mock at_pre_cmd"""
    cmdobj.hub = Mock()


class TestReportCommands(EvenniaCommandTest):
    @patch.object(create, "create_message", new=MagicMock())
    def test_report_cmd_base(self):
        """verify that the base command functionality works"""
        cmd = reports.ReportCmdBase

        # avoid test side-effects
        with patch.object(cmd, "at_pre_cmd", new=_mock_pre) as _:
            # no arguments
            self.call(cmd(), "", "You must provide a message.")
            # arguments, no target, no target required
            self.call(cmd(), "test", "Your report has been filed.")
            # arguments, custom success message
            custom_success = "custom success message"
            cmd.success_msg = custom_success
            self.call(cmd(), "test", custom_success)
            # arguments, no target, target required
            cmd.require_target = True
            self.call(cmd(), "test", "You must include a target.")

    @patch.object(create, "create_message", new=MagicMock())
    @patch.object(reports, "datetime_format", return_value="now")
    def test_ideas_list(self, mock_datetime_format):
        cmd = reports.CmdIdea

        fake_ideas = _MockQuerySet([TempMsg(message=f"idea {i+1}") for i in range(3)])
        expected = """\
Ideas you've submitted:
  idea 1 (submitted now)
  idea 2 (submitted now)
  idea 3 (submitted now)
"""

        with patch.object(cmd, "at_pre_cmd", new=_mock_pre) as _:
            # submitting an idea
            self.call(cmd(), "", "You must provide a message.")
            # arguments, no target, no target required
            self.call(cmd(), "test", "Thank you for your suggestion!")

            # viewing your submitted ideas
            with patch.object(reports.Msg.objects, "search_message", return_value=fake_ideas):
                self.call(cmd(), "", cmdstring="ideas", msg=expected)

    @patch.object(reports.evmenu, "EvMenu")
    def test_cmd_manage_reports(self, evmenu_mock):
        cmd = reports.CmdManageReports
        hub = Mock()

        with patch.object(reports, "_get_report_hub", return_value=hub) as _:
            # invalid report type fails
            self.call(
                cmd(), "", cmdstring="manage custom", msg="'custom' is not a valid report category."
            )
            # verify valid type triggers evmenu
            self.call(cmd(), "", cmdstring="manage bugs")
            evmenu_mock.assert_called_once_with(
                self.account,
                menu,
                startnode="menunode_list_reports",
                hub=hub,
                persistent=True,
            )
