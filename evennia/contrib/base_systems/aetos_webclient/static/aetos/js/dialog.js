/*
 * Aetos modal dialog.
 *
 * Used by the note editor and anything else needing focused input.
 *
 * A dialog is where keyboard accessibility is most often got wrong, and where
 * getting it wrong is most damaging: a focus trap that does not trap lets a
 * screen-reader user wander into the page behind the dialog and interact with
 * things they cannot see, with no way back.
 *
 * So this implements the modal dialog pattern properly:
 *
 *   - role="dialog" with aria-modal and an accessible name
 *   - focus moves into the dialog on open and RETURNS to the opener on close
 *   - Tab and Shift+Tab cycle within the dialog and cannot escape it
 *   - Escape cancels
 *   - the background is inert to pointer input
 *
 * Nothing here talks to the game. A dialog collects input; what happens next is
 * the caller's business.
 */

(function (window, document) {
    "use strict";

    var FOCUSABLE = [
        "button:not([disabled])",
        "input:not([disabled])",
        "textarea:not([disabled])",
        "select:not([disabled])",
        "a[href]",
        "[tabindex]:not([tabindex='-1'])"
    ].join(",");

    var openDialog = null;

    function focusableWithin(root) {
        return Array.prototype.slice.call(root.querySelectorAll(FOCUSABLE))
            .filter(function (element) {
                return element.offsetParent !== null || element === document.activeElement;
            });
    }

    function close(result) {
        if (!openDialog) {
            return false;
        }
        var current = openDialog;
        openDialog = null;

        if (current.overlay.parentNode) {
            current.overlay.parentNode.removeChild(current.overlay);
        }
        document.removeEventListener("keydown", current.keyHandler, true);

        // Focus must go back where it came from. A keyboard user whose focus is
        // dropped has to tab through the whole interface to return.
        if (current.opener && document.contains(current.opener)) {
            current.opener.focus();
        }
        if (current.onClose) {
            current.onClose(result);
        }
        return true;
    }

    /*
     * Open a dialog.
     *
     * `fields` describe the inputs; `onSubmit` receives their values. The caller
     * never touches the DOM, so every dialog in Aetos gets the same keyboard
     * behaviour rather than each reimplementing it slightly differently.
     */
    function open(options) {
        close(null);

        var overlay = document.createElement("div");
        overlay.className = "aetos-dialog__overlay";

        var dialog = document.createElement("div");
        dialog.className = "aetos-dialog";
        dialog.setAttribute("role", "dialog");
        dialog.setAttribute("aria-modal", "true");

        var titleId = "aetos-dialog-title";
        var heading = document.createElement("h2");
        heading.className = "aetos-dialog__title";
        heading.id = titleId;
        heading.textContent = options.title || "Aetos";
        dialog.setAttribute("aria-labelledby", titleId);
        dialog.appendChild(heading);

        if (options.description) {
            var description = document.createElement("p");
            description.className = "aetos-dialog__description";
            description.textContent = options.description;
            dialog.appendChild(description);
        }

        // Arbitrary content, for dialogs that show rather than ask -- the
        // privacy panel lists what is stored rather than collecting input.
        if (options.content) {
            dialog.appendChild(options.content);
        }

        var inputs = {};
        (options.fields || []).forEach(function (field) {
            var wrapper = document.createElement("div");
            wrapper.className = "aetos-dialog__field";

            var fieldId = "aetos-dialog-field-" + field.name;
            var label = document.createElement("label");
            label.setAttribute("for", fieldId);
            label.className = "aetos-dialog__label";
            label.textContent = field.label;

            var input;
            if (field.type === "textarea") {
                input = document.createElement("textarea");
                input.rows = field.rows || 5;
            } else if (field.type === "checkbox") {
                input = document.createElement("input");
                input.type = "checkbox";
                input.checked = !!field.value;
            } else {
                input = document.createElement("input");
                input.type = "text";
            }
            input.id = fieldId;
            input.className = "aetos-input";
            if (field.type !== "checkbox") {
                input.value = field.value || "";
            }

            wrapper.appendChild(label);
            wrapper.appendChild(input);
            dialog.appendChild(wrapper);
            inputs[field.name] = input;
        });

        var controls = document.createElement("div");
        controls.className = "aetos-dialog__controls";

        var submit = document.createElement("button");
        submit.type = "button";
        submit.className = "aetos-send";
        submit.textContent = options.submitLabel || "Save";
        submit.addEventListener("click", function () {
            var values = {};
            Object.keys(inputs).forEach(function (name) {
                var element = inputs[name];
                values[name] = element.type === "checkbox" ? element.checked : element.value;
            });
            close(values);
            if (options.onSubmit) {
                options.onSubmit(values);
            }
        });

        var cancel = document.createElement("button");
        cancel.type = "button";
        cancel.className = "aetos-list__button";
        /*
         * "Close" rather than "Cancel" when there is nothing to cancel.
         *
         * A dismiss-only dialog presents choices that act immediately -- the
         * settings dashboard is a list of places to go, not a form. Labelling
         * its only button "Cancel" would suggest the things already clicked
         * could be undone by pressing it.
         */
        cancel.textContent = options.dismissOnly ? "Close" : "Cancel";
        cancel.addEventListener("click", function () { close(null); });

        if (!options.dismissOnly) {
            controls.appendChild(submit);
        }

        /*
         * Extra actions, such as a destructive one alongside the main choice.
         *
         * Placed after the primary button so the dangerous option is never the
         * first thing a keyboard user lands on.
         */
        (options.extraActions || []).forEach(function (action) {
            var button = document.createElement("button");
            button.type = "button";
            button.className = "aetos-list__button";
            button.textContent = action.label;
            button.addEventListener("click", function () {
                close(null);
                action.run();
            });
            controls.appendChild(button);
        });

        controls.appendChild(cancel);
        dialog.appendChild(controls);

        overlay.appendChild(dialog);
        document.body.appendChild(overlay);

        function keyHandler(event) {
            if (event.key === "Escape") {
                event.preventDefault();
                close(null);
                return;
            }
            if (event.key !== "Tab") {
                return;
            }
            // Trap focus. Without this, Tab walks into the page behind the
            // dialog, where a screen-reader user can operate controls they
            // cannot see and have no obvious way back.
            var focusables = focusableWithin(dialog);
            if (!focusables.length) {
                return;
            }
            var first = focusables[0];
            var last = focusables[focusables.length - 1];
            if (event.shiftKey && document.activeElement === first) {
                event.preventDefault();
                last.focus();
            } else if (!event.shiftKey && document.activeElement === last) {
                event.preventDefault();
                first.focus();
            }
        }

        document.addEventListener("keydown", keyHandler, true);

        openDialog = {
            overlay: overlay,
            dialog: dialog,
            opener: options.opener || document.activeElement,
            keyHandler: keyHandler,
            onClose: options.onClose
        };

        var initial = focusableWithin(dialog)[0];
        if (initial) {
            initial.focus();
        }

        return { close: close, inputs: inputs, element: dialog };
    }

    window.AetosDialog = {
        open: open,
        close: close,
        isOpen: function () { return !!openDialog; }
    };

})(window, document);
