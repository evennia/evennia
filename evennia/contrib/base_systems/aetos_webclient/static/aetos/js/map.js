/*
 * Aetos map widget.
 *
 * Renders the local room graph as SVG, and -- with equal standing -- as text.
 *
 * THE TEXT MAP IS NOT A CAPTION.
 *
 * Blueprint section 47 requires every visual map to have a nonvisual equivalent.
 * That is easy to satisfy badly: bolt a description onto a picture and let the
 * two drift until the description describes a map that no longer exists.
 *
 * Both views here render from the same `map` store section, and the server
 * generates the coordinates and the surroundings description from the same
 * graph in one pass. Neither can silently disagree with the other.
 *
 * Both views are also equally operable. Clicking a room walks to it; so does
 * activating its entry in the text list, because both are real buttons calling
 * the same route function.
 */

(function (window, document) {
    "use strict";

    var CELL = 34;
    var ROOM_SIZE = 18;
    var PADDING = 14;

    /* ------------------------------------------------------------------
     * Routing
     * ------------------------------------------------------------------ */

    //: What an edge costs when a game says nothing.  C.19.
    //:
    //: One, so a game supplying no costs gets exactly the behaviour it had
    //: before weighting existed. Mirrors `map_layout.DEFAULT_EDGE_COST`.
    var DEFAULT_EDGE_COST = 1;

    //: Arithmetic hygiene rather than a judgement about what "expensive" means:
    //: a cost of 1e308 makes every comparison in the search meaningless.
    var MAX_EDGE_COST = 10000;

    function edgeCost(link) {
        var raw = link.cost;
        if (raw === undefined || raw === null || typeof raw === "boolean") {
            // `true` is not 1. It would be right by accident and wrong as a
            // habit, and the server refuses it for the same reason.
            return DEFAULT_EDGE_COST;
        }
        var cost = Number(raw);
        if (!isFinite(cost) || cost < 0) {
            // A negative edge would let a route improve by walking in circles,
            // which Dijkstra cannot express and no game means.
            return DEFAULT_EDGE_COST;
        }
        return Math.min(cost, MAX_EDGE_COST);
    }

    /*
     * Whether the game says this edge can currently be used.
     *
     * Absent means available. Treating silence as "blocked" would empty the map
     * of every game that has not adopted the field.
     */
    function edgeIsAvailable(link) {
        return link.available !== false;
    }

    /*
     * Cheapest route between two rooms, mirroring the server's `find_route`.
     *
     * Dijkstra, as C.19 permits -- costs are non-negative by construction, so
     * nothing more elaborate buys anything. **With no declared costs this is
     * exactly the breadth-first search it replaced**: every edge costs 1, so
     * the cheapest route is the one with fewest moves.
     *
     * Done client-side so clicking a room needs no round trip, and kept
     * identical in shape to the server's so the two cannot disagree about what
     * "shortest" means. A test pins both to the same fixtures.
     *
     * Edges the game marked unavailable are excluded. Aetos does not route
     * through a door the game says is shut -- and does not guess why it is
     * shut either, because C.19 forbids inferring skill, class, guild, weather
     * or roundtime restrictions.
     */
    function findRoute(mapData, from, to) {
        if (from === to) {
            return [];
        }
        var links = {};
        (mapData.rooms || []).forEach(function (room) { links[room.id] = []; });
        (mapData.exits || []).forEach(function (link) {
            if (links[link.from] && links[link.to] !== undefined &&
                    edgeIsAvailable(link)) {
                links[link.from].push(link);
            }
        });
        Object.keys(links).forEach(function (id) {
            links[id].sort(function (a, b) {
                return (a.direction || "").localeCompare(b.direction || "");
            });
        });

        var previous = {};
        previous[from] = null;
        var best = {};
        best[from] = 0;
        var settled = {};

        /*
         * A linear scan for the cheapest unsettled room rather than a heap.
         *
         * A map is tens of rooms, not thousands; a binary heap here would be
         * more code to get wrong for a saving nobody could measure. If a game
         * ever ships a map large enough to notice, the fix is a heap and the
         * tests will not change.
         */
        function cheapestUnsettled() {
            var chosen = null;
            var lowest = Infinity;
            Object.keys(best).forEach(function (room) {
                if (settled[room]) {
                    return;
                }
                // Ties break on room id, so two equally cheap routes resolve
                // the same way every time -- a map that suggests a different
                // equally-good route on each sync is one nobody can follow.
                if (best[room] < lowest || (best[room] === lowest && room < chosen)) {
                    lowest = best[room];
                    chosen = room;
                }
            });
            return chosen;
        }

        var current = cheapestUnsettled();
        while (current !== null) {
            if (current === to) {
                var steps = [];
                var cursor = to;
                while (previous[cursor]) {
                    steps.push(previous[cursor].direction);
                    cursor = previous[cursor].from;
                }
                steps.reverse();
                return steps;
            }
            settled[current] = true;

            (links[current] || []).forEach(function (link) {
                if (settled[link.to]) {
                    return;
                }
                var candidate = best[current] + edgeCost(link);
                if (best[link.to] === undefined || candidate < best[link.to]) {
                    best[link.to] = candidate;
                    previous[link.to] = { from: current, direction: link.direction };
                }
            });

            current = cheapestUnsettled();
        }
        return null;
    }

    /*
     * Exits the game says are shut, with its own stated reason.
     *
     * Surfaced rather than hidden: a player is entitled to know a door exists
     * and is closed, and a map that silently omits it looks like a map with a
     * missing room -- a worse thing to be looking at.
     *
     * The reason is never invented. Where the game supplies none the exit is
     * reported as blocked with no explanation, because "unknown" is preferable
     * to wrong (C.6).
     */
    function blockedExits(mapData) {
        return ((mapData && mapData.exits) || [])
            .filter(function (link) { return !edgeIsAvailable(link); })
            .map(function (link) {
                return {
                    from: link.from,
                    to: link.to,
                    direction: link.direction || "",
                    reason: typeof link.reason === "string" && link.reason
                        ? link.reason
                        : null
                };
            });
    }

    /* ------------------------------------------------------------------
     * SVG rendering
     * ------------------------------------------------------------------ */

    function svgElement(name, attrs) {
        var element = document.createElementNS("http://www.w3.org/2000/svg", name);
        Object.keys(attrs || {}).forEach(function (key) {
            element.setAttribute(key, attrs[key]);
        });
        return element;
    }

    function renderSvg(mapData, onWalk) {
        var positions = mapData.positions || {};
        var ids = Object.keys(positions);
        if (!ids.length) {
            return null;
        }

        var current = mapData.current;
        var currentZ = positions[current] ? positions[current][2] : 0;

        // Only the current Z level is drawn. Overlaying levels produces an
        // unreadable tangle, and a player is on exactly one of them.
        var visible = ids.filter(function (id) { return positions[id][2] === currentZ; });
        if (!visible.length) {
            return null;
        }

        var xs = visible.map(function (id) { return positions[id][0]; });
        var ys = visible.map(function (id) { return positions[id][1]; });
        var minX = Math.min.apply(null, xs);
        var minY = Math.min.apply(null, ys);
        var width = (Math.max.apply(null, xs) - minX) * CELL + ROOM_SIZE + (PADDING * 2);
        var height = (Math.max.apply(null, ys) - minY) * CELL + ROOM_SIZE + (PADDING * 2);

        var svg = svgElement("svg", {
            "class": "aetos-map__svg",
            viewBox: "0 0 " + width + " " + height,
            width: width,
            height: height,
            // The SVG is decorative: the adjacent text map carries the same
            // information in a form assistive technology can actually use.
            "aria-hidden": "true",
            focusable: "false"
        });

        function px(id) {
            return PADDING + ((positions[id][0] - minX) * CELL) + (ROOM_SIZE / 2);
        }
        function py(id) {
            return PADDING + ((positions[id][1] - minY) * CELL) + (ROOM_SIZE / 2);
        }

        (mapData.exits || []).forEach(function (link) {
            if (!positions[link.from] || !positions[link.to]) {
                return;
            }
            if (positions[link.from][2] !== currentZ || positions[link.to][2] !== currentZ) {
                return;
            }
            svg.appendChild(svgElement("line", {
                "class": "aetos-map__link",
                x1: px(link.from), y1: py(link.from),
                x2: px(link.to), y2: py(link.to)
            }));
        });

        var lookup = {};
        (mapData.rooms || []).forEach(function (room) { lookup[room.id] = room; });

        visible.forEach(function (id) {
            var room = lookup[id] || {};
            var isCurrent = id === current;
            var node = svgElement("rect", {
                "class": "aetos-map__room" + (isCurrent ? " aetos-map__room--current" : ""),
                x: px(id) - (ROOM_SIZE / 2),
                y: py(id) - (ROOM_SIZE / 2),
                width: ROOM_SIZE,
                height: ROOM_SIZE,
                rx: 3
            });
            if (!isCurrent && onWalk) {
                node.addEventListener("click", function () { onWalk(id); });
                node.classList.add("aetos-map__room--walkable");
            }
            var title = svgElement("title", {});
            title.textContent = room.name || id;
            node.appendChild(title);
            svg.appendChild(node);
        });

        return svg;
    }

    /* ------------------------------------------------------------------
     * Text rendering
     * ------------------------------------------------------------------ */

    /*
     * The non-visual map (blueprint section 47).
     *
     * Reads as prose rather than as a table of coordinates, because a player
     * navigating by ear needs "North: Tower Road", not "(3, -1, 0)".
     */
    /*
     * A route, written out.  A11Y-MAP-003.
     *
     * The visual map answers "how do I get there" by being looked at. That
     * answer is unavailable to a large part of the audience and unhelpful to
     * anyone who wants to know how far it is before committing, so the route
     * has a text form generated from the same step list the walker executes.
     *
     * Same list, not a parallel description -- if these could disagree, the
     * one a player was reading would eventually be the wrong one.
     */
    function describeRoute(mapData, steps, destinationId) {
        var rooms = {};
        (mapData.rooms || []).forEach(function (room) { rooms[room.id] = room; });

        var links = mapData.exits || [];
        var current = mapData.current;
        var described = [];

        steps.forEach(function (direction) {
            // Find where this step actually lands, so the description names
            // real rooms rather than repeating the direction back.
            var link = null;
            for (var i = 0; i < links.length; i++) {
                if (links[i].from === current && links[i].direction === direction) {
                    link = links[i];
                    break;
                }
            }
            var destination = link && rooms[link.to];
            described.push({
                direction: direction,
                to: link ? link.to : null,
                name: destination ? destination.name : null
            });
            if (link) {
                current = link.to;
            }
        });

        var target = rooms[destinationId];
        return {
            destination: target ? target.name : null,
            steps: described,
            // The number a player actually wants first. "Five steps" decides
            // whether to go now; the list decides how.
            count: described.length
        };
    }

    /*
     * Render a route as an ordered list.
     *
     * <ol>, not <ul>: the order is the information. A screen reader announcing
     * "1 of 5" gives a player their position in the journey for free, which an
     * unordered list does not.
     */
    function renderRoute(route) {
        var container = document.createElement("div");
        container.className = "aetos-map__route";

        var heading = document.createElement("h3");
        heading.className = "aetos-map__subheading";
        heading.textContent = route.destination
            ? "Route to " + route.destination
            : "Route";
        container.appendChild(heading);

        var summary = document.createElement("p");
        summary.className = "aetos-map__route-summary";
        summary.textContent = route.count === 1 ? "1 step" : route.count + " steps";
        container.appendChild(summary);

        var list = document.createElement("ol");
        list.className = "aetos-map__route-steps";
        route.steps.forEach(function (step) {
            var item = document.createElement("li");
            item.textContent = step.name
                ? step.direction + " to " + step.name
                : step.direction;
            list.appendChild(item);
        });
        container.appendChild(list);

        return container;
    }

    /*
     * Everywhere the player could go, searchable.  A11Y-MAP-004.
     *
     * Two sources, deliberately merged and deliberately labelled:
     *
     *   - rooms the map has walked to, which the game supplied
     *   - the player's own points of interest, which are notes with a room
     *     subject and never leave this browser
     *
     * Merged because a player looking for "the bank" does not care which of
     * those it came from. Labelled because one is the game's knowledge and the
     * other is their own, and confusing the two would be the same mistake as
     * confusing a game relationship with a private tag.
     *
     * Searchable because scanning a list of forty rooms is not navigation, and
     * because a list is the only form of the map available to somebody who
     * cannot see the picture.
     */
    function renderPlaces(mapData, pois, query, onWalk) {
        var container = document.createElement("div");
        container.className = "aetos-map__places";

        var needle = String(query || "").trim().toLowerCase();
        var current = mapData.current;
        var entries = [];

        (mapData.rooms || []).forEach(function (room) {
            if (room.id === current) {
                return;
            }
            entries.push({
                id: room.id,
                name: room.name || room.id,
                distance: typeof room.distance === "number" ? room.distance : null,
                own: false
            });
        });

        (pois || []).forEach(function (poi) {
            // A POI on a room the map already knows enriches that entry rather
            // than duplicating it -- two lines for one place is a worse list.
            var existing = null;
            for (var i = 0; i < entries.length; i++) {
                if (entries[i].name.toLowerCase() === String(poi.subject || "").toLowerCase()) {
                    existing = entries[i];
                    break;
                }
            }
            if (existing) {
                existing.own = true;
                existing.note = poi.body;
            } else {
                entries.push({
                    id: null,
                    name: poi.subject,
                    distance: null,
                    own: true,
                    note: poi.body
                });
            }
        });

        if (needle) {
            entries = entries.filter(function (entry) {
                return entry.name.toLowerCase().indexOf(needle) !== -1 ||
                    (entry.note || "").toLowerCase().indexOf(needle) !== -1;
            });
        }

        // Nearest first, then places with no known distance -- a player's own
        // POI on a room the map has not reached is still worth listing, just
        // not at the top where the reachable ones are.
        entries.sort(function (a, b) {
            if (a.distance === b.distance) {
                return a.name.localeCompare(b.name);
            }
            if (a.distance === null) { return 1; }
            if (b.distance === null) { return -1; }
            return a.distance - b.distance;
        });

        if (!entries.length) {
            var empty = document.createElement("p");
            empty.className = "aetos-map__empty";
            empty.textContent = needle
                ? "Nothing matches " + query + "."
                : "No other places known yet.";
            container.appendChild(empty);
            return container;
        }

        var list = document.createElement("ul");
        list.className = "aetos-list";
        entries.slice(0, 40).forEach(function (entry) {
            var item = document.createElement("li");
            var label = entry.name;
            if (entry.distance !== null) {
                label += ", " + entry.distance +
                    (entry.distance === 1 ? " room away" : " rooms away");
            }
            if (entry.own) {
                // Said in words, because the visual marker is unavailable to
                // exactly the player this list exists for.
                label += " (your note)";
            }

            if (entry.id && onWalk) {
                var button = document.createElement("button");
                button.type = "button";
                button.className = "aetos-list__button";
                button.textContent = label;
                button.addEventListener("click", function () { onWalk(entry.id); });
                item.appendChild(button);
            } else {
                // No id means the map cannot route there. A disabled button
                // would suggest it might; plain text says it cannot.
                item.textContent = label;
            }
            list.appendChild(item);
        });
        container.appendChild(list);
        return container;
    }

    function renderText(mapData, onWalk) {
        var surroundings = mapData.surroundings || {};
        var container = document.createElement("div");
        container.className = "aetos-map__text";

        var location = document.createElement("p");
        location.className = "aetos-map__location";
        location.textContent = surroundings.location
            ? "Current location: " + surroundings.location + "."
            : "Current location unknown.";
        container.appendChild(location);

        var exits = surroundings.exits || [];
        if (exits.length) {
            var exitHeading = document.createElement("h3");
            exitHeading.className = "aetos-map__subheading";
            exitHeading.textContent = "Exits";
            container.appendChild(exitHeading);

            var exitList = document.createElement("ul");
            exitList.className = "aetos-list";
            exits.forEach(function (exit) {
                var item = document.createElement("li");
                var button = document.createElement("button");
                button.type = "button";
                button.className = "aetos-list__button";
                // Names the destination when known: "North: Tower Road" tells a
                // player far more than "North".
                button.textContent = exit.name
                    ? exit.direction + ": " + exit.name
                    : exit.direction;
                if (onWalk) {
                    button.addEventListener("click", function () { onWalk(exit.to); });
                }
                item.appendChild(button);
                exitList.appendChild(item);
            });
            container.appendChild(exitList);
        }

        var landmarks = surroundings.landmarks || [];
        if (landmarks.length) {
            var landmarkHeading = document.createElement("h3");
            landmarkHeading.className = "aetos-map__subheading";
            landmarkHeading.textContent = "Nearby";
            container.appendChild(landmarkHeading);

            var landmarkList = document.createElement("ul");
            landmarkList.className = "aetos-list";
            landmarks.slice(0, 12).forEach(function (landmark) {
                var item = document.createElement("li");
                var button = document.createElement("button");
                button.type = "button";
                button.className = "aetos-list__button";
                var rooms = landmark.distance === 1 ? " room" : " rooms";
                button.textContent = (landmark.name || landmark.id) +
                    ", " + landmark.distance + rooms + " away";
                if (onWalk) {
                    button.addEventListener("click", function () { onWalk(landmark.id); });
                }
                item.appendChild(button);
                landmarkList.appendChild(item);
            });
            container.appendChild(landmarkList);
        }

        return container;
    }

    /* ------------------------------------------------------------------
     * Widget
     * ------------------------------------------------------------------ */

    function createMapWidget(services) {
        var sendCommand = services.sendCommand;
        var announce = services.announce || function () {};
        var queueRoute = services.queueRoute;
        // The player's own points of interest, if the notes store exists.
        // Absent on a browser with no storage, which simply means the places
        // list shows only what the game supplied.
        var listPois = services.listPois || null;

        // Kept across updates, so a sync arriving mid-search does not throw the
        // player back to an unfiltered list while they are reading it.
        var placesQuery = "";
        var pois = [];
        var lastRoute = null;
        var lastRouteOrigin = null;

        return {
            id: "map",
            // graphicalOnly is FALSE despite the SVG: the written surroundings
            // description is generated from the same graph as the picture, so
            // the map is not a graphic with a caption -- it is one dataset with
            // two equal renderings (A.29).
            accessibility: {
                landmarkLabel: "Local map",
                heading: "Map",
                keyboardOperable: true,
                liveUpdates: true
            },
            displayName: "Map",
            description: "Local room graph, visual and textual.",
            builtin: true,
            defaultRegion: "aside",
            defaultSize: { height: 260 },
            // No required capability: the default provider builds this from
            // ordinary rooms and exits, so it works on a pristine game.
            subscriptions: ["map"],

            /*
             * A stable skeleton, built once.  A11Y-FOCUS-005.
             *
             * Each region is a container that gets refilled; the containers
             * themselves, and the search input in particular, are never
             * replaced.
             *
             * The first version rebuilt the whole subtree on every render and
             * called focus() afterwards to put the player back in the search
             * box. That failed A0's own test, correctly: a sync arriving while
             * someone was typing would rebuild the field under them, and
             * restoring focus by hand only papers over a DOM that is being
             * destroyed for no reason. Not replacing the element is the fix;
             * putting focus back is the workaround.
             */
            mount: function (context) {
                context.element.classList.add("aetos-map");

                function region(className) {
                    var node = document.createElement("div");
                    node.className = className;
                    context.element.appendChild(node);
                    return node;
                }

                context.hosts = {
                    svg: region("aetos-map__svg-host"),
                    text: region("aetos-map__text-host"),
                    route: region("aetos-map__route-host"),
                    places: region("aetos-map__places-host")
                };

                var heading = document.createElement("h3");
                heading.className = "aetos-map__subheading";
                heading.textContent = "Places";

                var label = document.createElement("label");
                label.className = "aetos-visually-hidden";
                label.setAttribute("for", "aetos-map-search");
                label.textContent = "Search places";

                var input = document.createElement("input");
                input.type = "text";
                input.id = "aetos-map-search";
                input.className = "aetos-input aetos-map__search";
                input.placeholder = "Search places";

                context.searchInput = input;
                context.hosts.places.appendChild(heading);
                context.hosts.places.appendChild(label);
                context.hosts.places.appendChild(input);

                // The list is the only thing a keystroke changes.
                context.hosts.list = document.createElement("div");
                context.hosts.places.appendChild(context.hosts.list);

                context.element.appendChild(
                    (function () {
                        var note = document.createElement("p");
                        note.className = "aetos-map__note";
                        note.hidden = true;
                        context.hosts.note = note;
                        return note;
                    })()
                );
            },

            update: function (context, mapData) {
                var data = mapData || {};
                var panel = context.element.closest
                    ? context.element.closest("[data-aetos-widget]")
                    : null;
                var hasRooms = (data.rooms || []).length > 0;
                if (panel) {
                    // Emptiness, not the player's visibility choice.
                    panel.setAttribute("data-aetos-empty", hasRooms ? "false" : "true");
                }

                var hosts = context.hosts;
                if (!hosts) {
                    return;
                }
                if (!hasRooms) {
                    hosts.svg.textContent = "";
                    hosts.text.textContent = "";
                    hosts.route.textContent = "";
                    hosts.list.textContent = "";
                    return;
                }

                function fill(host, child) {
                    host.textContent = "";
                    if (child) {
                        host.appendChild(child);
                    }
                }

                function refreshPlaces() {
                    fill(hosts.list, renderPlaces(
                        data, pois, context.searchInput.value, walkTo));
                }

                function walkTo(roomId) {
                    var steps = findRoute(data, data.current, roomId);
                    if (!steps || !steps.length) {
                        /*
                         * Say why, but only what the game said.
                         *
                         * A player who can see a room on the map and cannot
                         * walk to it is owed better than "no route" -- that
                         * reads as a broken map rather than a shut door. So a
                         * blocked exit's own reason is repeated verbatim.
                         *
                         * Where the game supplied no reason, none is invented
                         * (C.19, C.6): "unknown" is preferable to wrong, and a
                         * guessed explanation is exactly the confident error
                         * that costs a player their trust in the map.
                         */
                        var blocked = blockedExits(data).filter(function (exit) {
                            return exit.reason;
                        });
                        announce(
                            blocked.length
                                ? "No route to that location. " +
                                  blocked[0].reason
                                : "No route to that location.",
                            { category: "system", priority: "important" }
                        );
                        return;
                    }

                    /*
                     * The route is written out before it is walked.
                     * A11Y-MAP-003.
                     *
                     * Not a confirmation step -- clicking still walks, because
                     * a dialog on every movement would punish everyone to
                     * satisfy a requirement about text. The route simply
                     * becomes readable: the destination and step count are
                     * announced, and the enumerated steps stay in the panel to
                     * be read at the player's own pace, or checked afterwards
                     * to see why they ended up somewhere unexpected.
                     */
                    lastRoute = describeRoute(data, steps, roomId);
                    fill(hosts.route, renderRoute(lastRoute));

                    // Queued as ordinary movement commands. The server decides
                    // whether each one succeeds; a locked door stops the route.
                    if (queueRoute) {
                        queueRoute(steps);
                    } else {
                        steps.forEach(function (step) { sendCommand(step); });
                    }

                    announce(
                        (lastRoute.destination
                            ? "Walking to " + lastRoute.destination + ", "
                            : "Walking ") +
                        steps.length + (steps.length === 1 ? " step." : " steps."),
                        { category: "movement", priority: "important" }
                    );
                }

                if (!context.searchBound) {
                    context.searchBound = true;
                    // Only the list is rebuilt, so the field the player is
                    // typing in is never touched and focus never moves.
                    context.searchInput.addEventListener("input", function () {
                        refreshPlaces();
                    });
                }

                fill(hosts.svg, renderSvg(data, walkTo));
                fill(hosts.text, renderText(data, walkTo));

                /*
                 * A route describes the map it was found on, so it is dropped
                 * when the map moves underneath it. Yesterday's route beside
                 * today's rooms is worse than no route at all.
                 */
                if (lastRoute && data.current !== lastRouteOrigin) {
                    lastRoute = null;
                    hosts.route.textContent = "";
                }
                lastRouteOrigin = data.current;

                refreshPlaces();

                if (listPois) {
                    // Asynchronous, so the first paint may have no POIs and a
                    // later one will. Only the list is refreshed, so this
                    // cannot disturb a player mid-search either.
                    listPois().then(function (found) {
                        pois = found || [];
                        refreshPlaces();
                    }).catch(function () {
                        pois = [];
                    });
                }

                // Approximate geometry is stated rather than hidden. A map
                // drawn with nudged rooms is still useful; a map that silently
                // lies about the world is not.
                var conflicts = (data.conflicts || []).length;
                hosts.note.hidden = !conflicts;
                hosts.note.textContent = conflicts
                    ? "Layout approximate here: " + conflicts +
                        (conflicts === 1 ? " room does" : " rooms do") +
                        " not fit the grid."
                    : "";
            }
        };
    }

    window.AetosMap = {
        createWidget: createMapWidget,
        findRoute: findRoute,
        blockedExits: blockedExits,
        edgeCost: edgeCost,
        edgeIsAvailable: edgeIsAvailable,
        DEFAULT_EDGE_COST: DEFAULT_EDGE_COST,
        describeRoute: describeRoute,
        renderRoute: renderRoute,
        renderPlaces: renderPlaces,
        renderText: renderText,
        renderSvg: renderSvg
    };

})(window, document);
