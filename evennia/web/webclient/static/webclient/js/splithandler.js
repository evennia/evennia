// Use split.js to create a basic ui
var SplitHandler = (function () {
  var num_splits = 0;
  var split_panes = {};

  var set_pane_types = function(splitpane, types) {
    split_panes[splitpane]['types'] = types;
  }

  var dynamic_split = function(splitpane, direction, update_method1, update_method2) {
    var first  = ++num_splits;
    var second = ++num_splits;

    var first_div  = $( '<div id="split_'+first +'" class="split split-'+direction+'" />' )
    var first_sub  = $( '<div id="split_'+first +'-sub"/>' )
    var second_div = $( '<div id="split_'+second+'" class="split split-'+direction+'" />' )
    var second_sub = $( '<div id="split_'+second+'-sub"/>' )

    // check to see if this pane contains the primary message window.
    contents = $('#'+splitpane).contents();
    if( contents ) {
      // it does, so move it to the first new div (TODO -- selectable between first/second?)
      contents.appendTo(first_sub);
    }

    first_div.append( first_sub );
    second_div.append( second_sub );

    // update the split_panes array to remove this split
    delete( split_panes[splitpane] );

    // now vaporize the current split_N-sub placeholder and create two new panes.
    $('#'+splitpane).parent().append(first_div);
    $('#'+splitpane).parent().append(second_div);
    $('#'+splitpane).remove();

    // And split
    Split(['#split_'+first,'#split_'+second], {
      direction: direction,
      sizes: [50,50],
      gutterSize: 4,
      minSize: [50,50],
    });

    // store our new splits for future splits/uses by the main UI.
    split_panes['split_'+first +'-sub'] = { 'types': [], 'update_method': update_method1 };
    split_panes['split_'+second+'-sub'] = { 'types': [], 'update_method': update_method2 };
  }


  var init = function(settings) {
    //change Mustache tags to ruby-style (Django gets mad otherwise)
    var customTags = [ '<%', '%>' ];
    Mustache.tags = customTags;

    var input_template = $('#input-template').html();
    Mustache.parse(input_template);

    Split(['#main','#input'], {
      direction: 'vertical',
      sizes: [90,10],
      gutterSize: 4,
      minSize: [50,50],
    });

    var input_render = Mustache.render(input_template);
    $('[data-role-input]').html(input_render);
    console.log("SplitHandler initialized");
  }

  return {
    init: init,
    set_pane_types: set_pane_types,
    dynamic_split: dynamic_split,
    split_panes: split_panes,
  }
})();
