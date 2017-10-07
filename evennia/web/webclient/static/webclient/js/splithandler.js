var SplitHandler = (function () {

  var init = function(settings) {
    Split(['#a', '#b'], {
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
