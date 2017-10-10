var SplitHandler = (function () {
  //initialize our split IDs
  var lastID = 1;

  var init = function(settings) {
    //change Mustache tags to ruby-style (Django gets mad otherwise)
    var customTags = [ '<%', '%>' ];
    Mustache.tags = customTags;
    //parse our templates to save time later
    var split_template = $('#split-template').html();
    Mustache.parse(split_template);

    var input_template = $('#input-template').html();
    Mustache.parse(input_template);

    var output_template = $('#output-template').html();
    Mustache.parse(output_template);

    var sizes = localStorage.getItem('split-sizes')

    if (sizes) {
        sizes = JSON.parse(sizes)
    } else {
        sizes = settings.sizes  // default sizes
    }
    var initial_split = Split(['#main', '#input'], {
      direction: 'vertical',
      sizes: sizes,
      gutterSize: 8,
      cursor: 'row-resize',
      minSize: [50,50],
      onDragEnd: function () {
        var wrapper = $("#inputform")
        var input = $("#inputcontrol")
        var prompt = $("#prompt")

        input.height(wrapper.height() - (input.offset().top - wrapper.offset().top));
        localStorage.setItem('split-sizes', JSON.stringify(initial_split.getSizes()));
      }
    })

    var input_render = Mustache.render(input_template);
    $('[data-role-input]').html(input_render);
    console.log("SplitHandler initialized");
  }

  function getSplitID() {
    var id = "split_" + lastID;
    lastID += 1;
    return id
  }

  var swapContent = function(move_from_selector, move_to_selector) {
    //Swap content between HTML items
    var move_from = $(move_from_selector);
    var move_to = $(move_to_selector);
    var move_from_children = move_from.children().detach();
    var move_to_children = move_to.children().detach();

    move_from.append(move_to_children);
    move_to.append(move_from_children);
  }

  var setTags = function(output_selector, tags) {
    var output_panel = $(output_selector)
    if (!output_panel.attr("data-role-output")) {
      console.log("Tried to set non-output element's tag handling")
      return
    }
    if (!output_panel) {
      console.log("Unable to find by selector")
      return
    }
    if (tags.constructor !== Array) {
      tags = [tags];
    }
    var formatted_tags = tags.join(", ")
    output_panel.data("tags", formatted_tags);
    console.log(selector + " tags are now " + JSON.stringify(formatted_tags));
  }

  var split = function(selector, direction) {
    // input a selector, split that into a directional 50/50 split
    var elem = $(selector);
    if (elem) {
      var parent_split = elem.closest(".split"); // if we already have a split, we'll still have the same elem
      var children = parent_split.children().detach(); // all child elements of current split
      if (direction === 'vertical'){
        var cursor = 'row-resize';
        var cursor = 'content';
        var horizontal = false;
      }
      else {
        var cursor = 'col-resize';
        var cls = 'split-horizontal';
        var horizontal = true;
      }
      var split_template = $('#split-template').html()
      var output_template = $('#output-template').html();

      var first_id = getSplitID();
      var second_id = getSplitID();
      var split_1 = Mustache.render(split_template, {horizontal: horizontal, id: first_id})
      var split_2 = Mustache.render(split_template, {horizontal: horizontal, id: second_id})

      var output_panel = Mustache.render(output_template, {id: "panel_" + second_id, tags: ["all"]})

      parent_split.append(split_1, split_2);
      var newsplit = Split(["#" + first_id, "#" + second_id], {
        direction: direction,
        sizes: [50, 50],
        guttersize: 8,
        cursor: cursor
      })

      $('#'+first_id).append(output_panel);
      $('#'+second_id).append(children);
    }
    else {
      console.log("No element found")
    }
  }

  return {
    init: init,
    split: split,
    swapContent: swapContent,
    setTags: setTags
  }
})();

$(document).ready(function() {
  SplitHandler.init({
    sizes: [50, 50]
  });
});
