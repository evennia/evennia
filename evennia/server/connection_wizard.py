"""
Link Evennia to external resources (wizard plugin for evennia_launcher)

"""
import sys
import pprint
from django.conf import settings
from evennia.utils.utils import list_to_string

class ConnectionWizard(object):

    def __init__(self):
        self.data = {}
        self.prev_node = None

    def display(self, text):
        "Show text"
        print(text)

    def ask_continue(self):
        "'Press return to continue'-prompt"
        input(" (Press return to continue)")

    def ask_node(self, options, prompt="Enter choice: ", default=None):
        """
        Retrieve options and jump to different menu nodes

        Args:
            options (dict): Node options on the form {key: (desc, callback), }
            prompt (str, optional): Question to ask
            default (str, optional): Default value to use if user hits return.

        """

        opt_txt = "\n".join(f" {key}: {desc}" for key, (desc, _, _) in options.items())
        self.display(opt_txt)

        while True:
            resp = input(prompt).strip()

            if not resp:
                if default:
                    resp = str(default)

            if resp.lower() in options:
                self.display(f" Selected '{resp}'.")
                desc, callback, kwargs = options[resp.lower()]
                callback(self, **kwargs)
            elif resp.lower() in ("quit", "q"):
                sys.exit()
            elif resp:
                # input, but nothing was recognized
                self.display(" Choose one of: {}".format(list_to_string(list(options))))

    def ask_yesno(self, prompt, default="yes"):
        """
        Ask a yes/no question inline.

        Kwargs:
            prompt (str): The prompt to ask.
            default (str): "yes" or "no", used if pressing return.
        Returns:
            reply (str): Either 'yes' or 'no'.

        """
        prompt = prompt + (" [Y]/N? " if default == "yes" else " Y/[N]? ")

        while True:
            resp = input(prompt).lstrip().lower()
            if not resp:
                resp = default.lower()
            if resp in ("yes", "y"):
                self.display(" Answered Yes.")
                return "yes"
            elif resp in ("no", "n"):
                self.display(" Answered No.")
                return "no"
            elif resp.lower() in ("quit", "q"):
                sys.exit()

    def ask_choice(self, prompt="> ", options=None, default=None):
        """
        Ask multiple-choice question, get response inline.

        Kwargs:
            prompt (str): Input prompt.
            options (list): List of options. Will be indexable by sequence number 1...
            default (int): The list index+1 of the default choice, if any
        Returns:
            reply (str): The answered reply.

        """
        opt_txt = "\n".join(f" {ind + 1}: {desc}" for ind, desc in enumerate(options))
        self.display(opt_txt)

        while True:
            resp = input(prompt).strip()

            if not resp:
                if default:
                    return options[int(default)]
            if resp.lower() in ("quit", "q"):
                sys.exit()
            if resp.isdigit():
                resp = int(resp) - 1
                if 0 <= resp < len(options):
                    selection = options[resp]
                    self.display(f" Selected '{selection}'.")
                    return selection
            self.display(" Select one of the given options.")

    def ask_input(self, prompt="> ", default=None, verify=True, max_len=None):
        """
        Get arbitrary input inline.

        Kwargs:
            prompt (str): The display prompt.
            default (str, optional): If empty input, use this.

        Returns:
            inp (str): The input given, or default.

        """
        while True:
            resp = input(prompt).strip()
            if not resp and default:
                resp = str(default)

            if resp.lower() == 'none':
                resp = ''
                ok = input("\n Leave blank? [Y]/N: ")
                if ok.lower() in ('n', 'no'):
                    continue
                elif ok.lower() in ('q', 'quit'):
                    sys.exit()
                return resp

            if verify:
                self.display(resp)
                if max_len:
                    nlen = len(resp)
                    if nlen > max_len:
                        self.display(f" This text is {nlen} characters long. Max is {max_len}.")
                        continue
                ok = input("\n Is the above looking correct? [Y]/N: ")
                if ok.lower() in ("n", "no"):
                    continue
                elif ok.lower() in ('q', 'quit'):
                    sys.exit()
            return resp


def node_start(wizard):
    text = """
    This wizard helps activate external networks with Evennia. It will create
    a config that will be attached to the bottom of the game settings file.

    Use `quit` at any time to abort and throw away any changes.
    """
    options = {
        "1": ("Add game to Evennia game index (also for closed dev games)",
              node_game_index_start, {}),
        "2": ("Add MSSP information (for mud-list crawlers)",
              node_mssp_start, {}),
        "3": ("View and Save created settings",
              node_view_and_apply_settings, {}),
               }

    wizard.display(text)
    wizard.ask_node(options)


# Evennia game index


def node_game_index_start(wizard, **kwargs):
    text = f"""
    The Evennia game index (http://games.evennia.com) lists both active Evennia
    games as well as games in various stages of development.

    You can put up your game in the index also if you are not (yet) open for
    players.  If so, put 'None' for the connection details. Just tell us you
    are out there and make us excited about your upcoming game!

    Please check the listing online first to see that your exact game name is
    not colliding with an existing game-name in the list (be nice!).
    """

    wizard.display(text)
    if wizard.ask_yesno("Continue adding/editing an Index entry?") == 'yes':
        node_game_index_fields(wizard)
    else:
        node_start(wizard)

def node_game_index_fields(wizard, status=None):

    # reset the listing if needed
    if not hasattr(wizard, "game_index_listing"):
        wizard.game_index_listing = settings.GAME_INDEX_LISTING

    # game status

    status_default = wizard.game_index_listing['game_status']
    text = f"""
    What is the status of your game?
        - pre-alpha: a game in its very early stages, mostly unfinished or unstarted
        - alpha: a working concept, probably lots of bugs and incomplete features
        - beta: a working game, but expect bugs and changing features
        - launched: a full, working game that may still be expanded upon and improved later

    Current value:
    {status_default}
    """

    options = ["pre-alpha", "alpha", "beta", "launched"]

    wizard.display(text)
    wizard.game_index_listing['game_status'] = \
        wizard.ask_choice("Select one: ", options)

    # short desc

    sdesc_default = wizard.game_index_listing.get('short_description', None)

    text = f"""
    Enter a short description of your game. Make it snappy and interesting!
    This should be at most one or two sentences (255 characters) to display by
    '{settings.SERVERNAME}' in the main game list. Line breaks will be ignored.

    Current value:
    {sdesc_default}
    """

    wizard.display(text)
    wizard.game_index_listing['short_description'] = \
        wizard.ask_input(default=sdesc_default, max_len=255)

    # long desc

    long_default = wizard.game_index_listing.get("long_description", None)

    text = f"""
    Enter a longer, full-length description. This will be shown when clicking
    on your game's listing. You can use \\n to create line breaks and may use
    Markdown formatting like *bold*, _italic_, [linkname](http://link) etc.

    Current value:
    {long_default}
    """

    wizard.display(text)
    wizard.game_index_listing['long_description'] = \
        wizard.ask_input(default=long_default)

    # listing contact

    listing_default = wizard.game_index_listing.get("listing_contact", None)
    text = f"""
    Enter a listing email-contact. This will not be visible in the listing, but
    allows us to get in touch with you should there be some listing issue (like
    a name collision) or some bug with the listing (us actually using this is
    likely to be somewhere between super-rarely and never).

    Current value:
    {listing_default}
    """

    wizard.display(text)
    wizard.game_index_listing['listing_contact'] = \
        wizard.ask_input(default=listing_default)

    # telnet hostname

    hostname_default = wizard.game_index_listing.get('telnet_hostname', None)
    text = f"""
    Enter the hostname to which third-party telnet mud clients can connect to
    your game. This would be the name of the server your game is hosted on,
    like `coolgame.games.com`, or `mygreatgame.se`.

    Write 'None' if you are not offering public telnet connections at this time.

    Current value:
    {hostname_default}
    """

    wizard.display(text)
    wizard.game_index_listing['telnet_hostname'] = \
        wizard.ask_input(default=hostname_default)


    # telnet port

    port_default = wizard.game_index_listing.get('telnet_port', None)
    text = f"""
    Enter the main telnet port. The Evennia default is 4000. You can change
    this with the TELNET_PORTS server setting.

    Write 'None' if you are not offering public telnet connections at this time.

    Current value:
    {port_default}
    """

    wizard.display(text)
    wizard.game_index_listing['telnet_port'] = \
        wizard.ask_input(default=port_default)


    # website

    website_default = wizard.game_index_listing.get('game_website', None)
    text = f"""
    Evennia is its own web server and runs your game's website. Enter the
    URL of the website here, like http://yourwebsite.com, here.

    Wtite 'None' if you are not offering a publicly visible website at this time.

    Current value:
    {website_default}
    """

    wizard.display(text)
    wizard.game_index_listing['game_website'] = \
        wizard.ask_input(default=website_default)

    # webclient

    webclient_default = wizard.game_index_listing.get('web_client_url', None)
    text = f"""
    Evennia offers its own native webclient. Normally it will be found from the
    game homepage at something like http://yourwebsite.com/webclient. Enter
    your specific URL here (when clicking this link you should launch into the
    web client)

    Wtite 'None' if you don't want to list a publicly accessible webclient.

    Current value:
    {webclient_default}
    """

    wizard.display(text)
    wizard.game_index_listing['web_client_url'] = \
        wizard.ask_input(default=webclient_default)

    if not (wizard.game_index_listing.get('web_client_url') or
            (wizard.game_index_listing.get('telnet_host'))):
        wizard.display(
            "\nNote: You have not specified any connection options. This means "
            "your game \nwill be marked as being in 'closed development' in "
            "the index.")

    wizard.display("\nDon't forget to inspect and save your changes.")

    node_start(wizard)


# MSSP


def node_mssp_start(wizard):

    text = f"""
    MSSP (Mud Server Status Protocol) allows online MUD-listing sites/crawlers
    to continuously monitor your game and list information about it. Some of
    this, like active player-count, Evennia will automatically add for you,
    whereas many fields is info about your game.

    To use MSSP you should generally have a publicly open game that external
    players can connect to.
    """

    wizard.mssp_table


# Admin

def _save_changes(wizard):
    """
    Perform the save
    """
    print("saving!")

def node_view_and_apply_settings(wizard):
    """
    Inspect and save the data gathered in the other nodes

    """
    pp = pprint.PrettyPrinter(indent=4)
    saves = False

    game_index_txt = "No changes to save for Game Index."
    if hasattr(wizard, "game_index_listing"):
        if wizard.game_index_listing != settings.GAME_INDEX_LISTING:
            game_index_txt = "No changes to save for Game Index."
        else:
            game_index_txt = pp.pformat(wizard.game_index_listing)
            saves = True

    text = game_index_txt

    print("- Game index:\n" + text)

    if saves:
        if wizard.ask_yesno("Do you want to save these settings?") == 'yes':
            _save_changes(wizard)
        else:
            print("Cancelled. Returning ...")
    wizard.ask_continue()
    node_start(wizard)

