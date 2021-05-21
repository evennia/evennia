/*
 *
 * Evennia Webclient text2html component
 *
 * This provides a library to render Evennia's Msg() ANSI, |-coded text into usable HTML
 *
 */

//
// Global Parser for text2html
//
var text2html = (function () {
    "use strict"

    let foreground = "color-102"; // state tracker for foreground css
    let background = "";          // state tracker for background css
    let underline  = "";          // state tracker for underlines css

    let pipecodes = /^(\|\[?[0-5][0-5][0-5])|(\|\[?=[a-z])|(\|[![]?[unrgybmcwxhRGYBMCWXH_/>*^-])/;
    // example         ^|000               or  ^|=a       or ^|_

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
    }


    // dumb convert any leading or trailing spaces/tabs to &nbsp; sequences
    var handleSpaces = function (text) {
        // TODO should probably get smart about not-replacing single spaces inside "normal" text
        return text.replace( /\t/g, "&nbsp;&nbsp;&nbsp;&nbsp;").replace( / /g, "&nbsp;");
    }


    // javascript doesn't have a native sprintf-like function for pretty printing numbers
    function zfill(string, size) {
        while (string.length < size) string = "0" + string;
        return string;
    }


    // given string starting with a pipecode  |xx
    //   return the css (if any) and text remainder
    var pipe2css = function(pipecode) {
        let regx = "";
        let css = null;

        regx = /^(\|\[?[nrgybmcwxhRGYBMCWX])|(\|\[?=[a-z])/;
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

        regx = /^(\|[hH])/;
        css = pipecode.match( regx );
        if( css != null ) {
            return ""; // TODO ignoring highlight/unhighlight, probably just another tracked state
        }

        regx = /^\|([0-9][0-9][0-9])/;
        css = pipecode.match( regx );
        if( css != null ) {
            return "color-" + zfill( (parseInt(css[1], 6) + 16).toString(), 3);
        }

        regx = /^\|\[([0-9][0-9][0-9])/;
        css = pipecode.match( regx );
        if( css != null ) {
            return "bgcolor-" + zfill( (parseInt(css[1], 6) + 16).toString(), 3);
        }

        regx = /^\|[_/>*^-]/; // TODO what to do with ugly codes:  |_  |/  |>  |*  |^  and  |-
        if( css != null ) {
            return "";        // ignored for now
        }

        return ""; // TODO This "defaults" (probably) bogus sequences like |!c, or |[>
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
    var parseMsg = function (text) {
        let html = "";
        foreground = "color-102"; // state tracker for foreground css
        background = "";          // state tracker for background css
        underline  = "";          // state tracker for underlines css

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

    return {
        parseMsg: parseMsg,
    }
})();
