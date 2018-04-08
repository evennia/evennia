// Use split.js to create a basic ui
var SplitHandler = (function () {
  var split_panes = {};
  var backout_list = new Array;

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

    // update the split_panes array to remove this pane name, but store it for the backout stack
    var backout_settings = split_panes[splitpane];
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

    // add our new split to the backout stack
    backout_list.push( {'pane1': pane_name1, 'pane2': pane_name2, 'undo': backout_settings} );
  }


  var undo_split = function() {
    // pop off the last split pair
    var back = backout_list.pop();
    if( !back ) {
      return;
    }

    // Collect all the divs/subs in play
    var pane1 = back['pane1'];
    var pane2 = back['pane2'];
    var pane1_sub = $('#'+pane1+'-sub');
    var pane2_sub = $('#'+pane2+'-sub');
    var pane1_parent = $('#'+pane1).parent();
    var pane2_parent = $('#'+pane2).parent();

    if( pane1_parent.attr('id') != pane2_parent.attr('id') ) {
      // sanity check failed...somebody did something weird...bail out
      console.log( pane1 );
      console.log( pane2 );
      console.log( pane1_parent );
      console.log( pane2_parent );
      return;
    }

    // create a new sub-pane in the panes parent
    var parent_sub = $( '<div id="'+pane1_parent.attr('id')+'-sub" class="split-sub" />' )

    // check to see if the special #messagewindow is in either of our sub-panes.
    var msgwindow = pane1_sub.find('#messagewindow')
    if( !msgwindow ) {
        //didn't find it in pane 1, try pane 2
        msgwindow = pane2_sub.find('#messagewindow')
    }
    if( msgwindow ) {
        // It is, so collect all contents into it instead of our parent_sub div
        // then move it to parent sub div, this allows future #messagewindow divs to flow properly
        msgwindow.append( pane1_sub.contents() );
        msgwindow.append( pane2_sub.contents() );
        parent_sub.append( msgwindow );
    } else {
        //didn't find it, so move the contents of the two panes' sub-panes into the new sub-pane
        parent_sub.append( pane1_sub.contents() );
        parent_sub.append( pane2_sub.contents() );
    }

    // clear the parent
    pane1_parent.empty();

    // add the new sub-pane back to the parent div
    pane1_parent.append(parent_sub);

    // pull the sub-div's from split_panes
    delete split_panes[pane1];
    delete split_panes[pane2];

    // add our parent pane back into the split_panes list for future splitting
    split_panes[pane1_parent.attr('id')] = back['undo'];
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
    undo_split: undo_split,
  }
})();
