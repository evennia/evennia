/*
 * Define the default GoldenLayout-based config
 *
 * The layout defined here will need to be customized based on which plugins
 * you are using and what layout you want players to see by default.
 *
 * This needs to be loaded in the HTML before the goldenlayout.js plugin
 *
 * The contents of the global variable will be overwritten by what is in the
 * browser's localstorage after visiting this site.
 *
 * For full documentation on all of the keywords see:
 *         http://golden-layout.com/docs/Config.html
 *
 */
var goldenlayout_config = { // Global Variable used in goldenlayout.js init()
    content: [{
        type: "column",
        content: [{
            type: "row",
            content: [{
                type: "column",
                content: [{
                    type: "component",
                    componentName: "Main",
                    isClosable: false, // remove the 'x' control to close this
                    tooltip: "Main - drag to desired position.",
                    componentState: {
                        types: "untagged",
                        updateMethod: "newlines",
                    },
                }]
            }],
//      }, {           // Uncomment the following to add a default hotbuttons component
//          type: "component",
//          componentName: "hotbuttons",
//          id: "inputComponent", // mark 'ignore this component during output message processing'
//          height: 6,
//          isClosable: false,
//      }, {
//            type: "component",
//            componentName: "input",
//            id: "inputComponent", // mark for ignore
//            height: 12,  // percentage
//            tooltip: "Input - The last input in the layout is always the default.",
        }, {
            type: "component",
            componentName: "input",
            id: "inputComponent", // mark for ignore
            height: 20,  // percentage
            isClosable: false, // remove the 'x' control to close this
            tooltip: "Input - The last input in the layout is always the default.",
        }]
    }]
};
