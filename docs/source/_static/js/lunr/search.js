//
// Using the pre-generated index file, set up a dynamic
// search mechanims that returns quick suggestions of the
// best matches you start to enter.
//

var lunrIndex,
    $results,
    documents;

function initLunr() {
  // retrieve the index file
  $.getJSON("_static/js/lunr/search_index.json")
    .done(function(index) {

        lunrIndex = lunr.Index.load(index)

        // documents = index;

        // lunrIndex = lunr(function(){
        //   this.ref('url')
        //   this.field('body')

        //   this.field("title", {
        //       boost: 10
        //   });

        //   documents.forEach(function(doc) {
        //     try {
        //       this.add(doc)
        //     } catch (e) {}
        //   }, this)
        // })
    })
    .fail(function(jqxhr, textStatus, error) {
        var err = textStatus + ", " + error;
        console.error("Error getting Lunr index file:", err);
    });
}

function search(query) {
  return lunrIndex.search(query).map(function(result) {
    return documents.filter(function(page) {
      try {
        console.log(page)
        return page.href === result.ref;
      } catch (e) {
        console.log('Error in search. ' + e)
      }
    })[0];
  });
}

function renderResults(results) {
  if (!results.length) {
    return;
  }

  // show first ten results
  results.slice(0, 10).forEach(function(result) {
    var $result = $("<li>");

    $result.append($("<a>", {
      href: result.url,
      text: "» " + result.title
    }));

    $results.append($result);
  });
}

function initUI() {
  $results = $("#lunrsearchresults");

  $("#lunrsearch").keyup(function(){
    // empty previous results
    $results.empty();

    // trigger search when at least two chars provided.
    var query = $(this).val();
    if (query.length < 2) {
      return;
    }

    var results = search(query);

    renderResults(results);
  });
}

initLunr();

$(document).ready(function(){
  initUI();
});
