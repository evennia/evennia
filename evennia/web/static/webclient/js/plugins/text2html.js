
/*
 *
 * Evennia Webclient text2html component
 *
 * This is used in conjunction with the main evennia.js library, which
 * handles all the communication with the Server.
 *
 */

//
// Global Parser for text2html
//
var text2html_plugin = (function () {
    "use strict"

    let asciiESC = String.fromCharCode(27); // string literal for ASCII ESC bytes

    let foreground = "color-102"; // state tracker for foreground css
    let background = "";          // state tracker for background css
    let underline  = "";          // state tracker for underlines css

    let pipecodes = /^(\|\[?[0-5][0-5][0-5])|(\|\[[0-9][0-9]?m)|(\|\[?=[a-z])|(\|[![]?[unrgybmcwxhRGYBMCWXH_/>*^-])/;
    // example         ^|000                or ^|[22m         or  ^|=a      or ^|_

    let csslookup = {
        "|n": "normal",
        "|r": "color-009",
        "|g": "color-010",
        "|y": "color-011",
        "|b": "color-012",
        "|m": "color-013",
        "|c": "color-014",
        "|w": "color-015",
        "|x": "color-008",
        "|R": "color-001",
        "|G": "color-002",
        "|Y": "color-003",
        "|B": "color-004",
        "|M": "color-005",
        "|C": "color-006",
        "|W": "color-007",
        "|X": "color-000",
        "|[r": "bgcolor-196",
        "|[g": "bgcolor-046",
        "|[y": "bgcolor-226",
        "|[b": "bgcolor-021",
        "|[m": "bgcolor-201",
        "|[c": "bgcolor-051",
        "|[w": "bgcolor-231",
        "|[x": "bgcolor-102",
        "|[R": "bgcolor-001",
        "|[G": "bgcolor-002",
        "|[Y": "bgcolor-003",
        "|[B": "bgcolor-004",
        "|[M": "bgcolor-005",
        "|[C": "bgcolor-006",
        "|[W": "bgcolor-007",
        "|[X": "bgcolor-000",
        "|=a": "color-016",
        "|=b": "color-232",
        "|=c": "color-233",
        "|=d": "color-234",
        "|=e": "color-235",
        "|=f": "color-236",
        "|=g": "color-237",
        "|=h": "color-238",
        "|=i": "color-239",
        "|=j": "color-240",
        "|=k": "color-241",
        "|=l": "color-242",
        "|=m": "color-243",
        "|=n": "color-244",
        "|=o": "color-245",
        "|=p": "color-246",
        "|=q": "color-247",
        "|=r": "color-248",
        "|=s": "color-249",
        "|=t": "color-250",
        "|=u": "color-251",
        "|=v": "color-252",
        "|=w": "color-253",
        "|=x": "color-254",
        "|=y": "color-255",
        "|=z": "color-231",
        "|[=a": "bgcolor-016",
        "|[=b": "bgcolor-232",
        "|[=c": "bgcolor-233",
        "|[=d": "bgcolor-234",
        "|[=e": "bgcolor-235",
        "|[=f": "bgcolor-236",
        "|[=g": "bgcolor-237",
        "|[=h": "bgcolor-238",
        "|[=i": "bgcolor-239",
        "|[=j": "bgcolor-240",
        "|[=k": "bgcolor-241",
        "|[=l": "bgcolor-242",
        "|[=m": "bgcolor-243",
        "|[=n": "bgcolor-244",
        "|[=o": "bgcolor-245",
        "|[=p": "bgcolor-246",
        "|[=q": "bgcolor-247",
        "|[=r": "bgcolor-248",
        "|[=s": "bgcolor-249",
        "|[=t": "bgcolor-250",
        "|[=u": "bgcolor-251",
        "|[=v": "bgcolor-252",
        "|[=w": "bgcolor-253",
        "|[=x": "bgcolor-254",
        "|[=y": "bgcolor-255",
        "|[=z": "bgcolor-231",
        // not sure what these nexts ones are actually supposed to map to
        "|[0m": "normal",
        "|[1m": "normal",
        "|[22m": "normal",
        "|[36m": "color-006",
        "|[37m": "color-015",
    }

    function ascii (l) {
        let a = new String(l); // force string
        return a.charCodeAt(0);
    }

    // dumb convert any leading or trailing spaces/tabs to &nbsp; sequences
    var handleSpaces = function (text) {
        // TODO should probably get smart about replacing spaces inside "normal" text
        return text.replace( /\t/g, "&nbsp;&nbsp;&nbsp;&nbsp;").replace( / /g, "&nbsp;");
    }


    // javascript doesn't have a native sprintf-like function
    function zfill(string, size) {
        while (string.length < size) string = "0" + string;
        return string;
    }


    // given string starting with a pipecode  |xx
    //   return the css (if any) and text remainder
    var pipe2css = function(pipecode) {
        let regx = "";
        let css = "color-102";

        regx = /^(\|\[?[nrgybmcwxhRGYBMCWX])/;
        css = pipecode.match( regx );
        if( css != null ) {
            return csslookup[ css[1] ];
        }

        regx = /^(\|\[?=[a-z])/;
        css = pipecode.match( regx );
        if( css != null ) {
            return csslookup[ css[1] ];
        }

        regx = /^(\|\[[0-9][0-9]?m)/;
        css = pipecode.match( regx );
        if( css != null ) {
            return csslookup[ css[1] ];
        }

        regx = /^(\|n)/;
        css = pipecode.match( regx );
        if( css != null ) {
            return "normal";
        }

        regx = /^(\|u)/;
        css = pipecode.match( regx );
        if( css != null ) {
            return "underline";
        }

        regx = /^\|([0-5][0-5][0-5])/;
        css = pipecode.match( regx );
        if( css != null ) {
            return "color-" + zfill( (parseInt(css[1], 6) + 16).toString(), 3);
        }

        regx = /^\|\[([0-5][0-5][0-5])/;
        css = pipecode.match( regx );
        if( css != null ) {
            return "bgcolor-" + zfill( (parseInt(css[1], 6) + 16).toString(), 3);
        }

        return css;
    }


    // convert any HTML sensitive characters to &code; format
    var htmlEscape = function (text) {
        text = text.replace(/&/g, "&amp;");
        text = text.replace(/</g, "&lt;");
        text = text.replace(/>/g, "&gt;");
        text = text.replace(/"/g, "&quot;");
        text = text.replace(/'/g, "&apos;");
        text = handleSpaces(text);
        return text;
    }


    // track stateful CSS 
    var trackCSS = function (css) {
        if( (typeof css !== 'string') && ! (css instanceof String) ) {
            css = "";
        }

        if( css.startsWith( "color-" ) ) {
            foreground = css;
        }

        if( css.startsWith( "bgcolor-" ) ) {
            background = css;
        }

        if( css === "underline" ) {
            underline = css;
        }

        if( css === "normal" ) {
            foreground = "color-102";
            background = "";
            underline = "";
        }

        return foreground + " " + background + " " + underline ;
    }


    /*
     *
     */
    var parse2HTML = function (text) {
        let html = "";
        foreground = "color-102"; // state tracker for foreground css
        background = "";          // state tracker for background css
        underline  = "";          // state tracker for underlines css

        // HACK: parse TELNET ASCII byte-by-byte, convert ESC's to |'s -- serverside "raw" bug?
        //       Bug is further proven out by the fact that |'s don't come through as doubles.
        let hack = new RegExp( String.fromCharCode(27) );
        if( text.match( hack ) ) {
            let chars = text.split(''); // to characters
            for( let n=0; n<chars.length; n++ ) {
                if( chars[n] === '|' ) {
                    console.log( 'Got Pipe' );
                    chars[n] = "&#124;";
                }
                if( ascii(chars[n]) === 27 ) {
                    chars[n] = '|';
                }
            }
            text = chars.join(''); // from character strings
        }

        let strings = text.split( /(\n|\|[\/])/ ); // newline or pipe-slash
        for( let x=0; x<strings.length; x++ ) {
            // hack double pipes -- convert them temporarily to HTML -- &#124;
            var string = strings[x].replace( /\|\|/g, "&#124;" );

            // special case for blank lines, avoid <div>'s with no HTML height
            if( string === "" ) {
                html += "<div>&nbsp;</div>";
                continue;
            }

            html += "<div>";

            let spans = string.split( "|" );

            // this split means there are 2 possible cases

            //   possibly-0-length leading span with "default" styling (may be the ONLY span)
            let span = spans[0].replaceAll("&#124;", "|"); // avoid htmlEscape mangling literal |'s
            if( span.length > 0 ) {
                html += "<span class='color-102'>" + htmlEscape(span) + "</span>";
            }

            //   "standard" span array of [xxxtext1, xxtext2, xxtext3], where x's are pipe-codes
            for( let n=1; n<spans.length; n++ ) {
                span = "|" + spans[n].replaceAll("&#124;", "|"); // avoid htmlEscape mangling |'s
                let pipecode = "";
                let remainder = span;

                let tags = span.match( pipecodes ); // match against large pipecode regex
                if( tags != null ) {
                    pipecode = tags[0];                       // matched text is the pipecode
                    remainder = span.replace( pipecode, "" ); // everything but the pipecode
                }

                let css = trackCSS( pipe2css( pipecode ) ); // find css associated with pipe-code
                html += "<span class='" + css + "'>" + htmlEscape(remainder) + "</span>";
            }

            html += "</div>";
        }

        return html;
    }

    // The Main text2html message capture fuction -- calls parse2HTML()
    var text2html = function (args, kwargs) {
        let options = window.options;
        if( !("text2html" in options) || options["text2html"] === false ) { return; }

        var mwins = window.plugins["goldenlayout"].routeMessage(args, kwargs);
        mwins.forEach( function (mwin) {
            mwin.append( parse2HTML( args[0]) ); // the heavy workload
            mwin.scrollTop(mwin[0].scrollHeight);
        });
    }

    //
    var onOptionsUI = function (parentdiv) {
        let options = window.options;
        var checked;

        checked = options["text2html"] ? "checked='checked'" : "";
        var text2html = $( [ "<label>",
                               "<input type='checkbox' data-setting='text2html' " + checked + "'>",
                               " Enable client-side Evennia ASCII message rendering",
                             "</label>"
                           ].join("") );
        text2html.on("change", window.plugins["options2"].onOptionCheckboxChanged);

        parentdiv.append(text2html);
    }

    //
    // Mandatory plugin init function
    var init = function () {
        let options = window.options;
        options["text2html"] = true;

        let Evennia = window.Evennia;
        Evennia.emitter.on("text2html", text2html); // capture "text2html" outfunc events

        console.log('Text2Html plugin initialized');
    }

    return {
        init: init,
        onOptionsUI: onOptionsUI,
        parse2HTML: parse2HTML,
    }
})();
plugin_handler.add("text2html_plugin", text2html_plugin);
