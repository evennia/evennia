/*
 *
 * Evennia Webclient default "send-text-on-enter-key" IO plugin
 *
 */
let font_plugin = (function () {

    const font_urls = {
        'B612 Mono': 'https://fonts.googleapis.com/css?family=B612+Mono&display=swap', 
        'Consolas': 'https://fonts.googleapis.com/css?family=Consolas&display=swap',
        'DejaVu Sans Mono': '/static/webclient/fonts/DejaVuSansMono.css',
        'Fira Mono': 'https://fonts.googleapis.com/css?family=Fira+Mono&display=swap',
        'Inconsolata': 'https://fonts.googleapis.com/css?family=Inconsolata&display=swap',
        'Monospace': '',
        'Roboto Mono': 'https://fonts.googleapis.com/css?family=Roboto+Mono&display=swap',
        'Source Code Pro': 'https://fonts.googleapis.com/css?family=Source+Code+Pro&display=swap',
        'Ubuntu Mono': 'https://fonts.googleapis.com/css?family=Ubuntu+Mono&display=swap',
    };

    //
    //
    var setStartingFont = function () {
        var fontfamily = localStorage.getItem("evenniaFontFamily");
        if( !fontfamily ) {
            $(document.body).css("font-family", fontfamily);
        }

        var fontsize = localStorage.getItem("evenniaFontSize");
        if( !fontsize ) {
            $(document.body).css("font-size", fontsize+"em");
        }
    }

    //
    //
    var getActiveFontFamily = function () {
        var family = "DejaVu Sans Mono";
        var fontfamily = localStorage.getItem("evenniaFontFamily");
        if( fontfamily != null ) {
            family = fontfamily;
        }
        return family;
    }

    //
    //
    var getActiveFontSize = function () {
        var size = "0.9";
        var fontsize = localStorage.getItem("evenniaFontSize");
        if( fontsize != null ) {
            size = fontsize;
        }
        return size;
    }

    //
    // 
    var onFontFamily = function (evnt) {
        var family = $(evnt.target).val();
        $(document.body).css("font-family", family);
        localStorage.setItem("evenniaFontFamily", family);
    }
 
    //
    //
    var onFontSize = function (evnt) {
        var size = $(evnt.target).val();
        $(document.body).css("font-size", size+"em");
        localStorage.setItem("evenniaFontSize", size);
    }

    //
    //
    var onOptionsUI = function (parentdiv) {
        var fontselect = $("<select>");
        var sizeselect = $("<select>");

        var fonts = Object.keys(font_urls);
        for( const font of fonts ) {
            fontselect.append( $("<option value='"+font+"'>"+font+"</option>") );
        }

        for (var x = 4; x < 21; x++) {
            var val = (x/10.0);
            sizeselect.append( $("<option value='"+val+"'>"+x+"</option>") );
        }

        fontselect.val( getActiveFontFamily() );
        sizeselect.val( getActiveFontSize() );

        // font change callbacks
        fontselect.on("change", onFontFamily);
        sizeselect.on("change", onFontSize);

        // add the font selection dialog control to our parentdiv
        parentdiv.append("<div style='font-weight: bold'>Font Selection:</div>");
        parentdiv.append(fontselect);
        parentdiv.append(sizeselect);
    }

    //
    // Font plugin init function (adds the urls for the webfonts to the page)
    // 
    var init = function () {
        var head = $(document.head);

        var fonts = Object.keys(font_urls);
        for (var x = 0; x < fonts.length; x++) {
            if ( fonts[x] != "Monospace" ) {
                var url = font_urls[ fonts[x] ];
                var link = $("<link href='"+url+"' rel='stylesheet'>");
                head.append( link );
            }
        }

        setStartingFont();
    }

    return {
        init: init,
        onOptionsUI: onOptionsUI,
    }
})();
window.plugin_handler.add("font", font_plugin);
