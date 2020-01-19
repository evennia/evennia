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
    //
    var onOptionsUI = function (parentdiv) {
        var fontselect = $('<select>');
        var sizeselect = $('<select>');

        var fonts = Object.keys(font_urls);
        for (var x = 0; x < fonts.length; x++) {
            var option = $('<option value="'+fonts[x]+'">'+fonts[x]+'</option>');
            fontselect.append(option);
        }

        for (var x = 4; x < 21; x++) {
            var val = (x/10.0);
            var option = $('<option value="'+val+'">'+x+'</option>');
            sizeselect.append(option);
        }

        fontselect.val('DejaVu Sans Mono'); // default value
        sizeselect.val('0.9'); // default scaling factor

        // font-family change callback
        fontselect.on('change', function () {
            $(document.body).css('font-family', $(this).val());
        });

        // font size change callback
        sizeselect.on('change', function () {
            $(document.body).css('font-size', $(this).val()+"em");
        });

        // add the font selection dialog control to our parentdiv
        parentdiv.append('<div style="font-weight: bold">Font Selection:</div>');
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
                var link = $('<link href="'+url+'" rel="stylesheet">');
                head.append( link );
            }
        }
    }

    return {
        init: init,
        onOptionsUI: onOptionsUI,
    }
})();
window.plugin_handler.add("font", font_plugin);
