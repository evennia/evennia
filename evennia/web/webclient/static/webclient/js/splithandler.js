var SplitHandler = (function () {

  var init = function(settings) {
    Split(['#a', '#b'], {
      direction: 'vertical',
      sizes: [75, 25],
      gutterSize: 8,
      cursor: 'row-resize'
    })
  }
  return {
    init: init
  }
})();

SplitHandler.init("hello!");
