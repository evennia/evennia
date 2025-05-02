let is_typing = (function (){
    let Evennia;
    let timeout = 0
    const state = {
        timeout: null,
        callback: null,
        is_typing: false,
        typing_players: [],
        cleanup_callback: null,
    }

    const sayCommands = ['say']

    /**
     * Create the containers that house our typing users
     */
    const createDialog = function() {
        const ele =[
            '<div id="istyping" class="content">',
            '<h5>Who\'s typing?</h4>',
            '<hr id="istypingdivider" />',
            '<div id="typingplayers"></div>',
            '</div>'
        ].join('\n')

        $('body').append(ele)
    }

    const playerElement =(name)=> `<div id="istyping-${name}" class="player-is-typing">${name}</div>`

    /**
     * The user has just started typing--set our flag, start our timeout callback, and
     * let the server know
     */
    const startedTyping = function () {
        state.is_typing = true;
        state.timeout = Date.now() + timeout;
        state.callback = setTimeout(stoppedTyping, timeout);

        sendIsTyping()
    }

    /**
     * The user is *still* typing--update our timeout and let the server know
     */
    const stillTyping = function () {
        state.timeout = Date.now() + timeout
        clearTimeout(state.callback)
        state.callback = setTimeout(stoppedTyping, timeout)

        sendIsTyping()
    }

    /**
     * The user has stopped typing--clean things up and tell the server
     */
    const stoppedTyping = function () {
        state.is_typing = false;
        clearTimeout(state.callback);
        state.callback = null;
        state.timeout = null;

        sendIsTyping()
    }

    /**
     * Make our commands array regex safe
     *
     * @param {string} - The contents of the user's command input
     */
    const escapeRegExp = function (text) {
        return text.replace(/[-[\]{}()*+?.,\\^$|#\s]/g, '\\$&');
    }

    /**
     * Fetch the "say" command's aliases and the notification timeout
     */
    const setup = function() {
        Evennia.msg('is_typing_setup');
    }

    /**
     * Add the provided aliases to the things we listen for
     *
     * @param {string[]} aliases - Array of "say" commands
     */
    const setSayAliases = function (aliases) {
        aliases.forEach(alias=>{
            const cmd = escapeRegExp(alias);

            // Is it already present?
            if (sayCommands.indexOf(cmd) === -1){
                sayCommands.push(escapeRegExp(alias)); // Nope!
            }
        })
    }

    /**
     * Sends a typing indicator to the server.
     *
     * @param {bool} state - The typing state, e.g., "typing" or "idle".
     */
    const sendIsTyping = function () {
        Evennia.msg('is_typing_state', null, {"state": state.is_typing})
    }

    const onLoggedIn = function () {
        setup()
    }

    /**
     * Sends a typing indicator to the server.
     *
     * @param {KeyboardEvent} event - The typing state, e.g., "typing" or "idle".
     */
    const onKeydown = function (event) {
        const regex = new RegExp(`^\W*(${sayCommands.reduce((acc, cur)=> acc + "|" + cur, "").substring(1)})`)
        const inputfield = $(".inputfield:focus");

        // A 'say' command is being used.
        if (Evennia.isConnected() &&
            inputfield.length === 1 &&
            event.key.length === 1 &&
            inputfield.val().match(regex)) {
            // Enter. Message sent. Reset.
            if (event.which === 13) {
                stoppedTyping()

            // Speaking just started. Set is_talking and timeout.
            } else if (!state.is_typing) {
                startedTyping();

            // Expiration is nearing. Update timeout.
            } else if (Date.now() + timeout > state.timeout) {
                stillTyping();

            }
        // Not talking anymore but state hasn't been updated yet.
        } else if (state.is_typing) {
            stoppedTyping();
        }
    }

    /**
     * Reset everything to defaults.
     */
    const onConnectionClose = function () {
        state.is_typing = false;
        state.timeout = null;
        state.typing_players = []

        if (state.callback) {
            clearTimeout(state.callback)
        }

        if (state.cleanup_callback) {
            clearTimeout(state.cleanup_callback)
        }
    }

    /**
     * Remove any timed out players and hide the div if no one is talking
     *
     */
    const cleanupTimedOutPlayers = function () {
        const now = Date.now();
        const timedOut = []

        state.typing_players.forEach((player, index)=>{
            if (player.timeout < now) {
                timedOut.push(index)
                $(`#istyping-${player}`).remove()
            }
        })

        timedOut.reverse().forEach(index=>state.typing_players.splice(index, 1))

        if (state.typing_players.length === 0) {
            clearTimeout(state.cleanup_callback)
            $('#istyping').hide();
        }
    }

    /**
     * This handles inbound comms from the server
     *
     * @param {{
     *  type: string - What type of response is it?
     *  payload - varies with type
     * }} kwargs
     */
    const is_typing = function (args, kwargs) {
        if ('type' in kwargs) {
            switch (kwargs.type) {
                case 'setup':
                    const {say_aliases, talking_timeout } = kwargs.payload
                    timeout = talking_timeout
                    setSayAliases(say_aliases)
                    break;

                case 'typing':
                    const player = state.typing_players.filter(player=>player.name === kwargs.payload.name)

                    // New talker
                    if (kwargs.payload.state &&
                        player.length === 0) {
                        state.typing_players.push({name: kwargs.payload.name, timeout: Date.now() + timeout})
                        $('#typingplayers').append(playerElement(kwargs.payload.name))

                    // Existing talker is still going
                    } else if (kwargs.payload.state &&
                        player.length > 0) {
                        player[0].timeout = Date.now() + timeout;

                    // They're done talking
                    } else {
                        state.typing_players = state.typing_players.filter(player=>player.name!== kwargs.payload.name)
                        $(`#istyping-${kwargs.payload.name}`).remove()
                    }

                    if (state.typing_players.length > 0 && !state.cleanup_callback) {
                        state.cleanup_callback = setTimeout(cleanupTimedOutPlayers, 100);
                        $('#istyping').show();

                    } else if (state.typing_players.length === 0 && state.cleanup_callback) {
                        clearTimeout(state.cleanup_callback)
                        state.cleanup_callback = null;
                        $('#istyping').hide();
                    }
                    break;

                default:
                    console.log("is_typing: Unknown case")
                    console.log(args)
                    console.log(kwargs)
            }
        }
    }

    const getState = () => state

    // Mandatory plugin init function
    const init = function () {
        let options = window.options;
        options["is_typing"] = true;
        Evennia = window.Evennia;

        Evennia.emitter.on("is_typing", is_typing);

        createDialog();

        console.log('Is Typing plugin initialized');
    }

    return {
        init,
        onLoggedIn,
        onKeydown,
        onConnectionClose,
        getState
    }
})()

window.plugin_handler.add("is_typing", is_typing)