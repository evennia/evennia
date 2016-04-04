from twisted.application.service import Service
from twisted.internet.task import LoopingCall

from evennia.contrib.gamedir_client.client import EvenniaGameDirClient
from evennia.utils import logger

# How often to sync to the server
_CLIENT_UPDATE_RATE = 60 * 30

class EvenniaGameDirService(Service):
    """
    Twisted Service that contains a LoopingCall for sending details on a
    game to the Evennia Game Directory.
    """
    name = 'GameDirectoryClient'

    def __init__(self):
        self.client = EvenniaGameDirClient(
            on_bad_request=self._die_on_bad_request)
        self.loop = LoopingCall(self.client.send_game_details)

    def startService(self):
        super(EvenniaGameDirService, self).startService()
        # TODO: Check to make sure that the client is configured.
        self.loop.start(_CLIENT_UPDATE_RATE)

    def stopService(self):
        if self.running == 0:
            # @reload errors if we've stopped this service.
            return
        super(EvenniaGameDirService, self).stopService()
        self.loop.stop()

    def _die_on_bad_request(self):
        """
        If it becomes apparent that our configuration is generating improperly
        formed messages to EGD, we don't want to keep sending bad messages.
        Stop the service so we're not wasting resources.
        """
        logger.log_infomsg(
            "Shutting down Evennia Game Directory client service due to "
            "invalid configuration.")
        self.stopService()
