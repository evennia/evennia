/*
 * Spawns plugin
 * REQUIRES: goldenlayout.js
 */
let spawns = (function () {

    var ignoreDefaultKeydown = false;

    var spawnmap = {};	// Mapping of regex/tag-pair

    var onAlterRegex = function (evnt) {
        var regex = $(evnt.target);
        var siblings = regex.siblings();
        spawnmap[regex.val()] = siblings.val();
        localStorage.setItem( "evenniaMessageRoutingSavedState", JSON.stringify(spawnmap) );
    }

    var onAlterTag = function (evnt) {
        var tag = $(evnt.target);
        var siblings = tag.siblings();
        spawnmap[siblings.val()] = tag.val();
        window.plugins["goldenlayout"].addKnownType( tag.val() );
        localStorage.setItem( "evenniaMessageRoutingSavedState", JSON.stringify(spawnmap) );
    }

    var onFocusIn = function (evnt) {
        ignoreDefaultKeydown = true;
    }

    var onFocusOut = function (evnt) {
        ignoreDefaultKeydown = false;
    }

    var onNewRegexRow = function (formdiv, regexstring, tagstring) {
        var div = $('<div>');
	var regex = $('<input class="regex" type=text value="'+regexstring+'"/>');
	var tag = $('<input class="tag" type=text value="'+tagstring+'"/>'); 
        regex.on('change', onAlterRegex );
        regex.on('focusin', onFocusIn );
        regex.on('focusout', onFocusOut );
        tag.on('change', onAlterTag );
        tag.on('focusin', onFocusIn );
        tag.on('focusout', onFocusOut );
        div.append(regex);
        div.append(tag);
	formdiv.append(div);
    }

    // Public

    //
    // onOptionsUI -- create an expandable/deletable row of regex/tag mapping pairs
    //            
    //            If there isn't a window with that tag mapped already, open a new one
    //
    var onOptionsUI = function (parentdiv) {
        var div = $('<div>');
        var button= $('<input type="button" value="New Regex/Tag Pair" />');
	button.on('click', function () { onNewRegexRow(div, '', ''); });
	div.append(button);

	for( regex in spawnmap ) {
	    onNewRegexRow(div, regex, spawnmap[regex] );
	}

	parentdiv.append('<h3>Message Routing:</h3>');
	parentdiv.append(div);
    }

    //
    // onText -- catch Text before it is routed by the goldenlayout router
    //           then test our list of regexes on the given text to see if it matches.
    //           If it does, rewrite the Text Type to be our tag value instead.
    //
    var onText = function (args, kwargs) {
        var txt = args[0];

	for( regex in spawnmap ) {
            if ( txt.match(regex) != null ) {
                kwargs['type'] = spawnmap[regex];
	    }
	}
    }


    //
    // OnKeydown -- if the Options window is open, capture focus
    //
    var onKeydown = function(evnt) {
        return ignoreDefaultKeydown;
    }


    //
    // init
    //
    var init = function () {
        var ls_spawnmap = localStorage.getItem( "evenniaMessageRoutingSavedState" );
        if( ls_spawnmap ) {
            spawnmap = JSON.parse(ls_spawnmap);
	    for( regex in spawnmap ) {
                window.plugins["goldenlayout"].addKnownType( spawnmap[regex] );
	    }
	}

        console.log('Client-Side Message Routing plugin initialized');
    }

    return {
        init: init,
	onOptionsUI: onOptionsUI,
        onText: onText,
        onKeydown: onKeydown,
    }
})();
window.plugin_handler.add("spawns", spawns);
