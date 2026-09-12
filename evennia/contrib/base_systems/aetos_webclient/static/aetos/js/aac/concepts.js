/*
 * Aetos AAC concepts.  Addendum A.59, A.60, A.61, A.65, A.69.
 *
 * THIS IS AN AAC ARCHITECTURE. IT IS NOT REVIEWED AAC SUPPORT.
 *
 * A.94 is explicit: do not claim useful AAC support until somebody familiar
 * with picture-supported communication has reviewed the concept organisation,
 * the symbol assumptions, the sentence strip, the terminology and the cognitive
 * load. That review has not happened. Nothing in Aetos's documentation says
 * "AAC support", and this comment is here so the next person to write that
 * sentence has to delete this paragraph first.
 *
 * What exists is the extension point: a concept model, a symbol provider seam,
 * a board and a sentence strip. An AAC practitioner can correct all of it
 * without touching the client's architecture, which is the useful thing to have
 * built in advance. What cannot be built in advance is the judgement.
 *
 * FOUR SEPARATE THINGS (A.60)
 *
 *   concept    -- what is meant             `help`
 *   label      -- what is on the key         "Help"
 *   text       -- what it says in a sentence "help"
 *   symbol     -- what is drawn              supplied by a pack, often nothing
 *   command    -- what is sent to the game   `say ...`
 *
 * `label` and `text` are separate because they are read in different places. A
 * key is a heading and reads better capitalised; a sentence is speech. Joining
 * the labels produced `say I Want Help`, which is what somebody's every message
 * would have looked like in public chat -- and looking like that is not a
 * neutral cost for a player already using a board to be heard.
 *
 * They are separated because they vary independently. Different AAC users know
 * different and mutually unfamiliar symbol sets (A.59); a game may want its own
 * wording; and the command for "north" is not the command for "help". Collapse
 * any two of them and one of those stops being changeable.
 *
 * NO INVENTED W3C IDS (A.60)
 *
 * `waiAdaptConcept` is `null` on every concept here, and that is deliberate
 * rather than unfinished. A W3C AAC Registry identifier is a claim that this
 * concept *is* that published concept, and Aetos has no way to verify one. A
 * plausible-looking invented ID would be worse than none: it would propagate
 * into other tools as though it had been checked.
 *
 * NO GENERATIVE INFERENCE (A.69, a hard MUST NOT)
 *
 * Every mapping in this file is a literal. Nothing here guesses what a player
 * means, rewrites game prose into symbols, or predicts a next concept. A system
 * that speaks *for* somebody has to be one they can predict completely --
 * otherwise it is putting words in their mouth, which is the specific harm AAC
 * exists to prevent.
 */

(function (window) {
    "use strict";

    /*
     * Categories, in the order they appear on the board.  A.65.
     *
     * "Common" first because it holds what is needed most urgently -- yes, no,
     * stop, help. A player who has to page through six categories to say "stop"
     * has been failed by the layout regardless of how good the symbols are.
     */
    var CATEGORIES = [
        { id: "common", label: "Common" },
        { id: "movement", label: "Movement" },
        { id: "people", label: "People" },
        { id: "actions", label: "Actions" },
        { id: "social", label: "Social" },
        { id: "questions", label: "Questions" },
        { id: "feelings", label: "Feelings" },
        { id: "objects", label: "Objects" },
        { id: "custom", label: "Mine" }
    ];

    /*
     * A concept.
     *
     * `commandTemplate` is null for most: they are *words*, and words are
     * assembled into a sentence which is then sent through one command. Only
     * concepts that are inherently an action -- a direction, "look" -- carry a
     * template of their own, and even then it is an ordinary game command that
     * the server judges exactly as if it had been typed (blueprint 2.4).
     *
     * A.65 says "only concepts with known meanings and appropriate mappings are
     * included". So there is no "attack", no "kill", no combat vocabulary: the
     * command for those is entirely game-specific, and a board that sent
     * `attack` to a game with no such command would fail silently at the moment
     * somebody most needed it to work.
     */
    function concept(id, label, category, commandTemplate, text) {
        return {
            id: id,
            label: label,
            /*
             * What this contributes to a sentence.
             *
             * Defaults to the lower-cased label, which is a mechanical
             * transformation rather than an inference -- A.69 forbids guessing
             * what somebody means, not knowing that a key cap is not speech.
             *
             * Given explicitly wherever lower-casing would be wrong. "I" is
             * the one in this set, and it is exactly the kind of thing that
             * has to be declared rather than derived: an English rule about
             * one pronoun is not something to encode as cleverness.
             */
            text: text || label.toLowerCase(),
            category: category,
            // See the header. Null until somebody can verify a real one.
            waiAdaptConcept: null,
            commandTemplate: commandTemplate || null
        };
    }

    var CONCEPTS = [
        // Common -- the ones that must never be more than one press away.
        concept("yes", "Yes", "common"),
        concept("no", "No", "common"),
        concept("stop", "Stop", "common"),
        concept("help", "Help", "common"),
        concept("please", "Please", "common"),
        concept("thank-you", "Thank you", "common"),
        concept("wait", "Wait", "common"),
        concept("sorry", "Sorry", "common"),

        // Movement. These carry command templates because a direction *is* an
        // action; the game decides whether it works.
        concept("north", "North", "movement", "north"),
        concept("south", "South", "movement", "south"),
        concept("east", "East", "movement", "east"),
        concept("west", "West", "movement", "west"),
        concept("up", "Up", "movement", "up"),
        concept("down", "Down", "movement", "down"),
        concept("in", "In", "movement", "in"),
        concept("out", "Out", "movement", "out"),
        concept("go", "Go", "movement"),
        concept("come", "Come", "movement"),

        // People.
        concept("i", "I", "people", null, "I"),
        concept("you", "You", "people"),
        concept("we", "We", "people"),
        concept("they", "They", "people"),
        concept("friend", "Friend", "people"),
        concept("everyone", "Everyone", "people"),

        // Actions.
        concept("look", "Look", "actions", "look"),
        concept("take", "Take", "actions"),
        concept("give", "Give", "actions"),
        concept("open", "Open", "actions"),
        concept("close", "Close", "actions"),
        concept("eat", "Eat", "actions"),
        concept("drink", "Drink", "actions"),
        concept("rest", "Rest", "actions"),
        concept("follow", "Follow", "actions"),
        concept("trade", "Trade", "actions"),

        // Social.
        concept("hello", "Hello", "social"),
        concept("goodbye", "Goodbye", "social"),
        concept("talk", "Talk", "social"),
        concept("listen", "Listen", "social"),
        concept("together", "Together", "social"),
        concept("alone", "Alone", "social"),

        // Questions.
        concept("what", "What", "questions"),
        concept("where", "Where", "questions"),
        concept("who", "Who", "questions"),
        concept("when", "When", "questions"),
        concept("why", "Why", "questions"),
        concept("how", "How", "questions"),

        /*
         * Feelings.
         *
         * Included because a communication board without them is one that lets
         * somebody transact but not converse -- and "I am not okay" is not a
         * transaction. The set is deliberately small and plain; a longer or
         * more nuanced list is exactly the kind of judgement A.94 asks a
         * practitioner to make rather than a developer.
         */
        concept("want", "Want", "feelings"),
        concept("need", "Need", "feelings"),
        concept("like", "Like", "feelings"),
        concept("dont-like", "Don't like", "feelings"),
        concept("happy", "Happy", "feelings"),
        concept("sad", "Sad", "feelings"),
        concept("tired", "Tired", "feelings"),
        concept("confused", "Confused", "feelings"),
        concept("okay", "Okay", "feelings"),
        concept("not-okay", "Not okay", "feelings"),

        // Objects. Generic on purpose: a specific inventory belongs to a game,
        // and Aetos assigns no meaning to a game's objects anywhere else
        // either.
        concept("thing", "Thing", "objects"),
        concept("food", "Food", "objects"),
        concept("water", "Water", "objects"),
        concept("money", "Money", "objects"),
        concept("weapon", "Weapon", "objects"),
        concept("key", "Key", "objects"),
        concept("door", "Door", "objects"),
        concept("here", "Here", "objects"),
        concept("there", "There", "objects")
    ];

    function byCategory(categoryId) {
        return CONCEPTS.filter(function (entry) {
            return entry.category === categoryId;
        });
    }

    function find(id) {
        var matches = CONCEPTS.filter(function (entry) { return entry.id === id; });
        return matches.length ? matches[0] : null;
    }

    /*
     * Turn a sequence of concepts into text.
     *
     * Joined with spaces, in the order chosen, and nothing else. No grammar, no
     * conjugation, no inserted articles, no reordering.
     *
     * That restraint is the point (A.69). "I want help" is what the player
     * built. A system that helpfully produced "I would like some help, please"
     * would be speaking for them -- and the first time it guessed wrong, it
     * would have said something they did not mean, in public, under their name.
     */
    function toText(concepts) {
        return (concepts || [])
            .map(function (entry) { return entry.text; })
            .join(" ")
            .trim();
    }

    window.AetosConcepts = {
        CATEGORIES: CATEGORIES.slice(),
        CONCEPTS: CONCEPTS.slice(),
        byCategory: byCategory,
        find: find,
        toText: toText,
        concept: concept
    };

})(window);
