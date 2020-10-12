/*
 * Spawns plugin
 * REQUIRES: goldenlayout.js
 */
let spawns = (function () {

    var spawnmap = {};	// { id1: { r:regex, t:tag } } pseudo-array of regex-tag pairs

    //
    // changes the spawnmap row's contents to the new regex/tag provided,
    // this avoids leaving stale regex/tag definitions in the spawnmap
    var onAlterTag = function (evnt) {
        var adult = $(evnt.target).parent();
        var children = adult.children();
        var id = $(adult).data('id');
        var regex = $(children[0]).val();// spaces before/after are valid regex syntax, unfortunately
        var mytag = $(children[1]).val().trim();

        if( mytag != "" && regex != "" ) {
            if( !(id in spawnmap) ) {
                spawnmap[id] = {};
            }
            spawnmap[id]["r"] = regex;
            spawnmap[id]["t"] = mytag;
            localStorage.setItem( "evenniaMessageRoutingSavedState", JSON.stringify(spawnmap) );
            window.plugins["goldenlayout"].addKnownType( mytag );
        }
    }

    //
    // deletes the entire regex/tag/delete button row.
    var onDeleteTag = function (evnt) {
        var adult = $(evnt.target).parent();
        var children = adult.children();
        var id = $(adult).data('id');
        delete spawnmap[id];
        localStorage.setItem( "evenniaMessageRoutingSavedState", JSON.stringify(spawnmap) );
        adult.remove(); // remove this set of input boxes/etc from the DOM
    }

    //
    var onFocusIn = function (evnt) {
        window.plugins["default_in"].setKeydownFocus(false);
    }

    //
    var onFocusOut = function (evnt) {
        window.plugins["default_in"].setKeydownFocus(true);
        onAlterTag(evnt); // percolate event so closing the pane, etc saves any last changes.
    }

    //
    // display a row with proper editting hooks
    var displayRow = function (formdiv, div, regexstring, tagstring) {
	var regex = $('<input class="regex" type=text value="'+regexstring+'"/>');
	var tag = $('<input class="tag" type=text value="'+tagstring+'"/>'); 
	var del = $('<input class="delete-regex" type=button value="X"/>'); 
        regex.on('change', onAlterTag );
        regex.on('focusin', onFocusIn );
        regex.on('focusout', onFocusOut );
        tag.on('change', onAlterTag );
        tag.on('focusin', onFocusIn );
        tag.on('focusout', onFocusOut );
        del.on('click', onDeleteTag );
        div.append(regex);
        div.append(tag);
        div.append(del);
	formdiv.append(div);
    }

    //
    // generate a whole new regex/tag/delete button row
    var onNewRegexRow = function (formdiv) {
        var nextid = 1;
        while( nextid in spawnmap ) { // pseudo-index spawnmap with id reuse
            nextid++;
        }
        var div = $("<div data-id='"+nextid+"'>");
        displayRow(formdiv, div, "", "");
    }


    // Public

    //
    // onOptionsUI -- display the existing spawnmap and a button to create more entries.
    //
    var onOptionsUI = function (parentdiv) {
        var formdiv = $('<div>');
        var button= $('<input type="button" value="New Regex/Tag Pair" />');
	button.on('click', function () { onNewRegexRow(formdiv) });
	formdiv.append(button);

        // display the existing spawnmap
	for( var id in spawnmap ) {
            var div = $("<div data-id='"+id+"'>");
	    displayRow(formdiv, div, spawnmap[id]["r"], spawnmap[id]["t"] );
	}

	parentdiv.append('<div style="font-weight: bold">Message Routing:</div>');
	parentdiv.append(formdiv);
    }

    //
    // onText -- catch Text before it is routed by the goldenlayout router
    //           then test our list of regexes on the given text to see if it matches.
    //           If it does, rewrite the Text Type to be our tag value instead.
    //
    var onText = function (args, kwargs) {
        var div = $("<div>" + args[0] + "</div>");
        var txt = div.text();
	for( var id in spawnmap ) {
            var regex = spawnmap[id]["r"];
            if ( txt.match(regex) != null ) {
                kwargs['type'] = spawnmap[id]["t"];
	    }
	}
        return false;
    }


    //
    // init
    //
    var init = function () {
        var ls_spawnmap = localStorage.getItem( "evenniaMessageRoutingSavedState" );
        if( ls_spawnmap ) {
            spawnmap = JSON.parse(ls_spawnmap);
	    for( var id in spawnmap ) {
                window.plugins["goldenlayout"].addKnownType( spawnmap[id]["t"] );
	    }
	}

        console.log('Client-Side Message Routing plugin initialized');
    }

    return {
        init: init,
	onOptionsUI: onOptionsUI,
        onText: onText,
    }
})();
window.plugin_handler.add("spawns", spawns);
