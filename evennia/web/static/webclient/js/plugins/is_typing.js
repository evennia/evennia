let is_typing = (function (){
    let Evennia;
    // 10 second timeout
    const timeout = 10 * 1000
    const state = {
        timeout: null,
        callback: null,
        is_typing: false,
        typing_players: [],
        cleanup_callback: null,
    }

    const sayCommands = ['say']

    const createDialog = function() {
        const ele =[
            '<div id="istyping" class="content">',
            '<div id="typingplayers"></div>',
            '</div>'
        ].join('\n')

        $('body').append(ele)
    }

    const playerElement =(name)=> `<div id="istyping-${name}" class="player-is-typing">${name} is typing...</div>`

    const startedTyping = function () {
        state.is_typing = true;
        state.timeout = Date.now() + timeout;
        state.callback = setTimeout(stoppedTyping, timeout);

        sendIsTyping()
    }

    const stillTyping = function () {
        state.timeout = Date.now() + timeout
        clearTimeout(state.callback)
        state.callback = setTimeout(stoppedTyping, timeout)

        sendIsTyping()
    }

    const stoppedTyping = function () {
        state.is_typing = false;
        clearTimeout(state.callback);
        state.callback = null;
        state.timeout = null;

        sendIsTyping()
    }

    // Make our commands array regex safe
    const escapeRegExp = function (text) {
        return text.replace(/[-[\]{}()*+?.,\\^$|#\s]/g, '\\$&');
    }

    // Get the say command's aliases
    const requestSayAliases = function () {
        Evennia.msg('is_typing_get_aliases')
    }

    const setSayAliases = function (aliases) {
        aliases.forEach(alias=>sayCommands.push(escapeRegExp(alias)))
    }

    // Update server
    const sendIsTyping = function () {
        Evennia.msg('is_typing_state', [state.is_typing])
    }

    const onLoggedIn = function () {
        requestSayAliases();
    }

    // Listen for talk commands
    const onKeydown = function (event) {
        const regex = new RegExp(`^\W*(${sayCommands.reduce((acc, cur)=> acc + "|" + cur, "").substring(1)})`)
        const inputfield = $(".inputfield:focus");

        // A 'say' command is being used.
        if (Evennia.isConnected() &&
            inputfield.length === 1 &&
            inputfield.val().match(regex)) {
            // Enter. Message sent. Reset.
            if (event.which === 13) {
                stoppedTyping()

            // Speaking just started. Set is_talking and timeout.
            } else if (!state.is_typing) {
                startedTyping();

            // Expiration is nearing. Update timeout.
            } else if (Date.now() + 5 * 1000 > state.timeout) {
                stillTyping();

            }
        // Not talking anymore but state hasn't been updated yet.
        } else if (state.is_typing) {
            stoppedTyping();
        }
    }

    // Reset everything
    const onConnectionClose = function () {
        state.is_typing = false;
        state.timeout = null;
        state.typing_players = []

        if (state.callback) {
            clearTimeout(state.callback)
        }

        if (state.cleanup_callback) {
            clearInterval(state.cleanup_callback)
        }
    }

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
            clearInterval(state.cleanup_callback)
            $('#istyping').hide();
        }
    }

    const is_typing = function (args, kwargs) {
        if ('type' in kwargs) {
            switch (kwargs.type) {
                case 'aliases':
                    setSayAliases(kwargs.payload)
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
                        state.cleanup_callback = setInterval(cleanupTimedOutPlayers, 100);
                        $('#istyping').show();

                    } else if (state.typing_players.length === 0 && state.cleanup_callback) {
                        clearInterval(state.cleanup_callback)
                        state.cleanup_callback = null;
                        $('#istyping').hide();
                    }
                    break;

                default:
                    console.log("Default case")
                    console.log(args)
                    console.log(kwargs)
            }
        }
    }

    const getState = () => state

    //
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