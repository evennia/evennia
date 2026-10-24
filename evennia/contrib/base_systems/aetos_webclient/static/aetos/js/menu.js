/*
 * Aetos context menu.
 *
 * Contextual actions on an entity: look, get, talk, whatever the game exposes.
 *
 * ACCESSIBILITY IS THE HARD PART, NOT THE MENU.
 *
 * A right-click menu is trivial and excludes a lot of people. Blueprint section
 * 51 requires context menus to open by the Context Menu key and Shift+F10 as
 * well, and to be readable and operable by a screen reader. So this implements
 * the ARIA menu pattern properly:
 *
 *   - the trigger declares aria-haspopup and aria-expanded
 *   - the menu is role="menu" with role="menuitem" children
 *   - focus MOVES into the menu on open and RETURNS to the trigger on close,
 *     because a keyboard user who loses their place has to start over
 *   - Up/Down/Home/End move between items, Escape closes, Tab closes
 *   - the menu is modal to the keyboard while open: arrow keys do not leak out
 *
 * Aetos never decides whether an action is legal. Every item sends an ordinary
 * command and the server rules on it, exactly as if it had been typed.
 */

(function (window, document) {
    "use strict";

    var openMenu = null;

    function closeOpenMenu(returnFocus) {
        if (!openMenu) {
            return false;
        }
        var trigger = openMenu.trigger;
        if (openMenu.element.parentNode) {
            openMenu.element.parentNode.removeChild(openMenu.element);
        }
        if (trigger) {
            trigger.setAttribute("aria-expanded", "false");
            if (returnFocus) {
                // Returning focus is not a nicety. A keyboard user whose focus
                // is dropped to the document has to tab back through the whole
                // interface to get where they were.
                trigger.focus();
            }
        }
        openMenu = null;
        return true;
    }

    function focusItem(items, index) {
        if (!items.length) {
            return;
        }
        var bounded = (index + items.length) % items.length;
        items.forEach(function (item, position) {
            // Roving tabindex: exactly one item is tabbable at a time, which is
            // what makes Tab exit the menu rather than walk through it.
            item.setAttribute("tabindex", position === bounded ? "0" : "-1");
        });
        items[bounded].focus();
    }

    /*
     * Open a menu of actions for a trigger element.
     *
     * `actions` are the entity's own actions, delivered with the entity, so a
     * menu can never be rendered against the wrong target.
     */
    function openContextMenu(options) {
        var trigger = options.trigger;
        var actions = options.actions || [];
        var onCommand = options.onCommand;
        var sanitize = options.sanitize;
        var label = options.label || "Actions";

        closeOpenMenu(false);

        if (!actions.length) {
            if (options.announce) {
                options.announce("No actions available for " + label + ".");
            }
            return null;
        }

        var menu = document.createElement("ul");
        menu.className = "aetos-menu";
        menu.setAttribute("role", "menu");
        menu.setAttribute("aria-label", "Actions for " + label);

        var items = [];
        var lastGroup = null;

        actions.forEach(function (action) {
            /*
             * Group separator.
             *
             * Blueprint section 24 separates the game's own actions from the
             * player's private ones, and the distinction is real rather than
             * cosmetic: a server action sends a command the game will act on,
             * while a local action only edits data in this browser. A player
             * marking someone an Enemy must not wonder whether the game was
             * told.
             */
            var group = action.group || "server";
            if (lastGroup !== null && group !== lastGroup) {
                var divider = document.createElement("li");
                divider.className = "aetos-menu__separator";
                divider.setAttribute("role", "separator");
                menu.appendChild(divider);
            }
            lastGroup = group;

            var listItem = document.createElement("li");
            listItem.setAttribute("role", "none");

            var button = document.createElement("button");
            button.type = "button";
            button.className = "aetos-menu__item aetos-menu__item--" + group;
            button.setAttribute("role", "menuitem");
            button.setAttribute("tabindex", "-1");
            if (action.display && sanitize) {
                button.appendChild(sanitize(action.display));
            } else {
                button.textContent = action.label;
            }
            // Local actions say so, so a screen-reader user hears the same
            // distinction the separator conveys visually.
            if (group === "local") {
                button.setAttribute("aria-description", "private to this browser");
            }
            button.addEventListener("click", function () {
                closeOpenMenu(true);
                if (typeof action.run === "function") {
                    // A local action mutates local data. It never reaches the
                    // command dispatcher, so it cannot be sent to the game.
                    action.run();
                } else if (onCommand) {
                    onCommand(action.command);
                }
            });

            listItem.appendChild(button);
            menu.appendChild(listItem);
            items.push(button);
        });

        menu.addEventListener("keydown", function (event) {
            var index = items.indexOf(document.activeElement);
            switch (event.key) {
            case "ArrowDown":
                focusItem(items, index + 1);
                break;
            case "ArrowUp":
                focusItem(items, index - 1);
                break;
            case "Home":
                focusItem(items, 0);
                break;
            case "End":
                focusItem(items, items.length - 1);
                break;
            case "Escape":
                closeOpenMenu(true);
                break;
            case "Tab":
                // Tab leaves the menu rather than cycling inside it, which is
                // what the ARIA menu pattern expects.
                closeOpenMenu(true);
                return;
            default:
                return;
            }
            event.preventDefault();
            event.stopPropagation();
        });

        // Positioned relative to the trigger's own container so the menu tracks
        // its widget when panels move.
        var host = trigger.closest("[data-aetos-widget]") || document.body;
        host.appendChild(menu);

        trigger.setAttribute("aria-expanded", "true");
        openMenu = { element: menu, trigger: trigger, items: items };

        focusItem(items, 0);
        return menu;
    }

    /*
     * Make an element open a context menu.
     *
     * Bound to all three documented ways of asking for one: right-click, the
     * Context Menu key, and Shift+F10. Only the first is obvious, and it is the
     * one a keyboard user cannot press.
     */
    function attachContextMenu(element, getOptions) {
        element.setAttribute("aria-haspopup", "menu");
        element.setAttribute("aria-expanded", "false");

        element.addEventListener("contextmenu", function (event) {
            event.preventDefault();
            openContextMenu(getOptions());
        });

        element.addEventListener("keydown", function (event) {
            var isContextKey = event.key === "ContextMenu";
            var isShiftF10 = event.shiftKey && event.key === "F10";
            if (!isContextKey && !isShiftF10) {
                return;
            }
            event.preventDefault();
            openContextMenu(getOptions());
        });
    }

    // A click elsewhere dismisses the menu. Focus is NOT returned here: the user
    // is deliberately looking somewhere else, and yanking focus back would fight
    // them.
    document.addEventListener("click", function (event) {
        if (openMenu && !openMenu.element.contains(event.target) &&
                event.target !== openMenu.trigger) {
            closeOpenMenu(false);
        }
    });

    window.AetosMenu = {
        attach: attachContextMenu,
        open: openContextMenu,
        close: closeOpenMenu,
        isOpen: function () { return !!openMenu; }
    };

})(window, document);
