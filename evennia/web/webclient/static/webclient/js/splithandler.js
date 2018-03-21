// Use split.js to create a basic ui
var SplitHandler = (function () {
  var split_panes = {};

  var set_pane_types = function(splitpane, types) {
    split_panes[splitpane]['types'] = types;
  }


  var dynamic_split = function(splitpane, direction, pane_name1, pane_name2, update_method1, update_method2, sizes) {
    // find the sub-div of the pane we are being asked to split
    splitpanesub = splitpane + '-sub';

    // create the new div stack to replace the sub-div with.
    var first_div  = $( '<div id="'+pane_name1+'" class="split split-'+direction+'" />' )
    var first_sub  = $( '<div id="'+pane_name1+'-sub" class="split-sub" />' )
    var second_div = $( '<div id="'+pane_name2+'" class="split split-'+direction+'" />' )
    var second_sub = $( '<div id="'+pane_name2+'-sub" class="split-sub" />' )

    // check to see if this sub-pane contains anything
    contents = $('#'+splitpanesub).contents();
    if( contents ) {
      // it does, so move it to the first new div-sub (TODO -- selectable between first/second?)
      contents.appendTo(first_sub);
    }
    first_div.append( first_sub );
    second_div.append( second_sub );

    // update the split_panes array to remove this pane name
    delete( split_panes[splitpane] );

    // now vaporize the current split_N-sub placeholder and create two new panes.
    $('#'+splitpane).append(first_div);
    $('#'+splitpane).append(second_div);
    $('#'+splitpane+'-sub').remove();

    // And split
    Split(['#'+pane_name1,'#'+pane_name2], {
      direction: direction,
      sizes: sizes,
      gutterSize: 4,
      minSize: [50,50],
    });

    // store our new split sub-divs for future splits/uses by the main UI.
    split_panes[pane_name1] = { 'types': [], 'update_method': update_method1 };
    split_panes[pane_name2] = { 'types': [], 'update_method': update_method2 };
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

    split_panes['main']  = { 'types': [], 'update_method': 'append' };

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
