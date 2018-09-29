/*
 * Popups GUI functions plugin
 */
let popups_plugin = (function () {

    //
    // openPopup
    var openPopup = function (dialogname, content) {
        var dialog = $(dialogname);
        if (!dialog.length) {
            console.log("Dialog " + renderto + " not found.");
            return;
        }

        if (content) {
            var contentel = dialog.find(".dialogcontent");
            contentel.html(content);
        }
        dialog.show();
    }

    //
    // closePopup
    var closePopup = function (dialogname) {
        var dialog = $(dialogname);
        dialog.hide();
    }

    //
    // togglePopup
    var togglePopup = function (dialogname, content) {
        var dialog = $(dialogname);
        if (dialog.css('display') == 'none') {
            openPopup(dialogname, content);
        } else {
            closePopup(dialogname);
        }
    }

    //
    // createDialog
    var createDialog = function (dialogid, dialogtitle, content) {
        var dialog = $( [
            '<div id="'+ dialogid +'" class="dialog">',
            ' <div class="dialogtitle">'+ dialogtitle +'<span class="dialogclose">&times;</span></div>',
            '  <div class="dialogcontentparent">',
            '   <div id="'+ dialogid +'content" class="dialogcontent">'+ content +'</div>',
            '  </div>',
            ' </div>',
            '</div>',
            ].join("\n") );

        $('body').append( dialog );

        $('#'+ dialogid +' .dialogclose').bind('click', function (event) { $('#'+dialogid).hide(); });
    }

    //
    // User clicked on a dialog to drag it
    var doStartDragDialog = function (event) {
        var dialog = $(event.target).closest(".dialog");
        dialog.css('cursor', 'move');

        var position = dialog.offset();
        var diffx = event.pageX;
        var diffy = event.pageY;

        var drag = function(event) {
            var y = position.top + event.pageY - diffy;
            var x = position.left + event.pageX - diffx;
            dialog.offset({top: y, left: x});
        };

        var undrag = function() {
            $(document).unbind("mousemove", drag);
            $(document).unbind("mouseup", undrag);
            dialog.css('cursor', '');
        }

        $(document).bind("mousemove", drag);
        $(document).bind("mouseup", undrag);
    }

    //
    // required plugin function
    var init = function () {
        // Makes dialogs draggable
        $(".dialogtitle").bind("mousedown", doStartDragDialog);

        console.log('Popups Plugin Initialized.');
    }

    return {
        init: init,
        openPopup: openPopup,
        closePopup: closePopup,
        togglePopup: togglePopup,
        createDialog: createDialog,
    }
})()
plugin_handler.add('popups', popups_plugin);
