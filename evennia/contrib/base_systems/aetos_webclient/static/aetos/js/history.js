/*
 * Aetos event history.  Addendum A.10, A.12, A.18.
 *
 * The transcript, but navigable: filtered by channel, searchable, and paged.
 *
 * WHY A SECOND VIEW OF THE SAME TEXT. The console is a stream, and a stream is
 * the right shape for following a game as it happens and the wrong shape for
 * every other question. "What did Renn say?" and "what happened while I was
 * away?" are both answered by scrolling and squinting, which is not an answer.
 *
 * This reads the canonical log, so it shows what happened rather than what the
 * console currently displays. That distinction becomes load-bearing when E2
 * adds display rules: a line the player filtered out of their console is still
 * here, because hiding is a display choice and this is not the display.
 *
 * IT DOES NOT ANNOUNCE. Same rule as the Current State View: the announcement
 * manager already speaks for these events, and a second voice for the same
 * facts means hearing everything twice. Review Mode is how this surface talks,
 * and only when asked.
 *
 * PAGED, NOT VIRTUALISED. A.12 forbids virtualisation that evicts a focused or
 * reviewed node, and the simplest way to honour that is not to virtualise:
 * render a bounded page and give the player controls to move between pages. A
 * hundred rows is fast in any browser, and nothing can be evicted from under a
 * reader because nothing is evicted at all.
 */

(function (window, document) {
    "use strict";

    //: Events per page. A.12 suggests 100. Small enough to render instantly,
    //: large enough that paging is rare.
    var PAGE_SIZE = 100;

    //: Channels offered as filters. The full category list is thirteen long,
    //: which is a menu rather than a control; these are the ones a player
    //: reaches for.
    var FILTERS = [
        { id: "", label: "All" },
        { id: "tell", label: "Tells" },
        { id: "chat", label: "Chat" },
        { id: "combat", label: "Combat" },
        { id: "system", label: "System" }
    ];

    function createHistoryWidget(services) {
        var log = services.canonicalLog || null;
        var review = services.review || null;

        var filter = "";
        var query = "";
        var page = 0;

        function matching() {
            if (!log) {
                return [];
            }
            var needle = query.trim().toLowerCase();
            return log.all().filter(function (event) {
                if (filter && event.category !== filter) {
                    return false;
                }
                if (needle && displayable(event).toLowerCase().indexOf(needle) === -1) {
                    return false;
                }
                // Structured events with no text have nothing to show here.
                // They are still in the log, and the Current State View is
                // where their effect is visible.
                return !!event.originalText;
            });
        }

        /*
         * The text of an event as a person reads it.
         *
         * `originalText` is what the server sent, markup and all. Assigning it
         * to `textContent` showed the player `<span class="color-002">` and the
         * MXP anchors verbatim -- every coloured line, unconditionally -- and
         * searching it meant a query for "span" matched everything while a
         * query for a word split by a colour change matched nothing.
         *
         * The fallback covers an event from before `plainText` existed, where
         * the two strings are the same anyway.
         */
        function displayable(event) {
            return event.plainText === undefined
                ? (event.originalText || "")
                : (event.plainText || "");
        }

        function renderRows(host) {
            var events = matching();
            var pages = Math.max(1, Math.ceil(events.length / PAGE_SIZE));
            if (page >= pages) {
                page = pages - 1;
            }

            host.textContent = "";

            if (!events.length) {
                var empty = document.createElement("p");
                empty.className = "aetos-history__empty";
                empty.textContent = query
                    ? "Nothing matches " + query + "."
                    : "No events yet.";
                host.appendChild(empty);
                return { events: events, pages: pages };
            }

            // Newest last, matching the console, so the two read the same way
            // round. A history that ran the other way would be a second thing
            // to learn for no benefit.
            var start = events.length - ((page + 1) * PAGE_SIZE);
            var slice = events.slice(Math.max(0, start), events.length - (page * PAGE_SIZE));

            var list = document.createElement("ol");
            list.className = "aetos-history__list";
            // Numbered from the real position in the filtered set, so "3 of 5"
            // in Review Mode and the number here agree.
            list.setAttribute("start", String(Math.max(1, events.length - ((page + 1) * PAGE_SIZE) + 1)));

            slice.forEach(function (event) {
                var item = document.createElement("li");
                item.className = "aetos-history__row aetos-history__row--" + event.category;
                item.setAttribute("data-aetos-event", event.id);

                // The channel is said in words, not shown as a colour: the
                // player most likely to be reading history rather than the
                // console is the one least able to see a tint.
                var channel = document.createElement("span");
                channel.className = "aetos-history__channel";
                channel.textContent = event.category;

                var body = document.createElement("span");
                body.className = "aetos-history__text";
                body.textContent = displayable(event);

                item.appendChild(channel);
                item.appendChild(body);
                list.appendChild(item);
            });

            host.appendChild(list);
            return { events: events, pages: pages };
        }

        return {
            id: "history",
            accessibility: {
                landmarkLabel: "Event history",
                heading: "History",
                description: "Everything that has happened, filtered and searchable.",
                keyboardOperable: true,
                // It updates as events arrive, but it never announces -- the
                // announcement manager already speaks for these, and Review
                // Mode is how this surface talks when asked (A11Y-LOG-002).
                liveUpdates: true
            },
            displayName: "History",
            description: "Searchable transcript, by channel.",
            builtin: true,
            defaultRegion: "sidebar",
            defaultSize: { height: 320 },
            /*
             * No store subscriptions: this reads the canonical log, which is
             * not a store section. It is refreshed by a hook the shell drives
             * from the pipeline instead -- see `registerRefresh` below.
             *
             * Subscribing to a store section would have been the easy wiring
             * and the wrong one: the history would then redraw when *state*
             * changed rather than when an *event* arrived, which are different
             * things and only coincidentally correlated.
             */
            subscriptions: [],

            mount: function (context) {
                context.element.setAttribute("data-aetos-history", "");
                // Explicitly off. The console is the live surface; this is the
                // one you come to on purpose.
                context.element.setAttribute("aria-live", "off");

                var controls = document.createElement("div");
                controls.className = "aetos-history__controls";

                var label = document.createElement("label");
                label.className = "aetos-visually-hidden";
                label.setAttribute("for", "aetos-history-search");
                label.textContent = "Search history";

                var input = document.createElement("input");
                input.type = "text";
                input.id = "aetos-history-search";
                input.className = "aetos-input";
                input.placeholder = "Search history";

                var channels = document.createElement("div");
                channels.className = "aetos-history__filters";
                channels.setAttribute("role", "group");
                channels.setAttribute("aria-label", "Filter by channel");

                controls.appendChild(label);
                controls.appendChild(input);
                controls.appendChild(channels);

                var rows = document.createElement("div");
                rows.className = "aetos-history__rows";
                /*
                 * Focusable, because it scrolls.
                 *
                 * Arrow keys scroll whatever has focus, so a scrolling region
                 * outside the tab order cannot be scrolled by keyboard at all:
                 * the player can see there is more and has no way to reach it.
                 * Third instance of this in the client -- it is invisible to
                 * anyone testing with a mouse wheel, and axe is the only thing
                 * that has ever caught it.
                 *
                 * A focusable region needs a name, or it is announced as an
                 * unlabelled group.
                 */
                rows.setAttribute("tabindex", "0");
                rows.setAttribute("role", "region");
                rows.setAttribute("aria-label", "Event history");

                var pager = document.createElement("div");
                pager.className = "aetos-history__pager";

                context.element.appendChild(controls);
                context.element.appendChild(rows);
                context.element.appendChild(pager);

                context.hosts = { rows: rows, pager: pager, channels: channels, input: input };

                function refresh() {
                    var result = renderRows(rows);
                    pager.textContent = "";
                    if (result.pages <= 1) {
                        return;
                    }
                    // Stated in words as well as being controls, so a player
                    // knows there is more before they go looking for it.
                    var status = document.createElement("span");
                    status.className = "aetos-history__page";
                    status.textContent = "Page " + (page + 1) + " of " + result.pages;
                    pager.appendChild(status);

                    [["Older", 1], ["Newer", -1]].forEach(function (entry) {
                        var button = document.createElement("button");
                        button.type = "button";
                        button.className = "aetos-list__button";
                        button.textContent = entry[0];
                        button.disabled = entry[1] > 0
                            ? page >= result.pages - 1
                            : page <= 0;
                        button.addEventListener("click", function () {
                            page += entry[1];
                            refresh();
                        });
                        pager.appendChild(button);
                    });
                }

                context.refresh = refresh;

                // Only the rows are rebuilt when typing, so the field the
                // player is using is never replaced (A11Y-FOCUS-005) -- the
                // lesson A3 learned the hard way.
                input.addEventListener("input", function () {
                    query = input.value;
                    page = 0;
                    refresh();
                });

                FILTERS.forEach(function (entry) {
                    var button = document.createElement("button");
                    button.type = "button";
                    button.className = "aetos-list__button aetos-history__filter";
                    button.textContent = entry.label;
                    button.setAttribute("aria-pressed", entry.id === filter ? "true" : "false");
                    button.addEventListener("click", function () {
                        filter = entry.id;
                        page = 0;
                        channels.querySelectorAll("button").forEach(function (other) {
                            other.setAttribute("aria-pressed", other === button ? "true" : "false");
                        });
                        refresh();
                    });
                    channels.appendChild(button);
                });

                if (review) {
                    var reviewButton = document.createElement("button");
                    reviewButton.type = "button";
                    reviewButton.className = "aetos-list__button";
                    reviewButton.textContent = "Review mode";
                    reviewButton.addEventListener("click", function () {
                        review.toggle();
                        reviewButton.setAttribute(
                            "aria-pressed", review.isActive() ? "true" : "false");
                    });
                    reviewButton.setAttribute("aria-pressed", "false");
                    controls.appendChild(reviewButton);
                }

                /*
                 * Throttled.
                 *
                 * During a flood the log can grow faster than a browser can
                 * usefully re-render a hundred rows, and a history that
                 * stutters during a fight is a history nobody reads during a
                 * fight. A quarter of a second is imperceptible for reading
                 * and cheap enough to survive combat.
                 */
                var pending = null;
                function throttledRefresh() {
                    if (pending !== null) {
                        return;
                    }
                    pending = window.setTimeout(function () {
                        pending = null;
                        refresh();
                    }, 250);
                }

                if (services.registerRefresh) {
                    services.registerRefresh(throttledRefresh);
                }
                context.cancelRefresh = function () {
                    if (pending !== null) {
                        window.clearTimeout(pending);
                        pending = null;
                    }
                };

                refresh();
            },

            update: function (context) {
                if (context.refresh) {
                    context.refresh();
                }
            },

            destroy: function (context) {
                if (context && context.cancelRefresh) {
                    context.cancelRefresh();
                }
            }
        };
    }

    window.AetosHistory = {
        createWidget: createHistoryWidget,
        PAGE_SIZE: PAGE_SIZE,
        FILTERS: FILTERS
    };

})(window, document);
