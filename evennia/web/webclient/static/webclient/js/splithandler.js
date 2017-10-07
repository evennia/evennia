var SplitHandler = (function () {

  var init = function(settings) {
    Split(['#main', '#input'], {
      direction: 'vertical',
      sizes: [90, 10],
      gutterSize: 8,
      cursor: 'row-resize'
    })
  }
  return {
    init: init
  }
})();

SplitHandler.init("hello!");
