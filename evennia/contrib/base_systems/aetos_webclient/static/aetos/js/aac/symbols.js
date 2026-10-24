/*
 * Aetos symbol provider.  Addendum A.62, A.63, A.64.
 *
 *     AetosSymbolProvider.getSymbol(concept) -> { src, alt, license, attribution }
 *
 * WHY AETOS SHIPS NO SYMBOLS
 *
 * An earlier version of this comment said the major AAC symbol sets are all
 * restrictively licensed. **That was wrong**, and the correction is worth
 * keeping rather than quietly replacing, because the wrong reason led to the
 * right decision and that is exactly how a bad assumption survives.
 *
 * What is actually true, checked rather than assumed:
 *
 *   ARASAAC     CC BY-NC-SA. The NonCommercial clause is a real blocker for
 *               bundling: Aetos is BSD-3-Clause and games that install it may
 *               charge money. A *player* may install it; the contrib may not
 *               ship it.
 *   Mulberry    CC BY-SA 4.0, and its own documentation explicitly permits use
 *               "in any project or product, commercial or otherwise" with
 *               attribution and share-alike on derived symbols. Bundling is
 *               legally fine.
 *
 * So licensing is not the reason for Mulberry. **Coverage is.** Mulberry has
 * 3,436 symbols whose largest categories are country flags, country maps and
 * professions -- it is a vocabulary set built to supplement a core board for
 * adults, not to be one. It has no symbol for `yes`, `no`, `stop`, `please`,
 * `thank you`, `sorry` or `friend`.
 *
 * Bundling it would produce a board where the six most urgent words are the
 * only ones without a picture, which is worse than a board with no pictures at
 * all: the inconsistency is itself a thing to decode, and it is worst exactly
 * where hesitation costs most.
 *
 * ARASAAC does cover that core vocabulary. It is also the one Aetos may not
 * ship. That is not a coincidence -- a complete pictographic system is the kind
 * of work whose authors reasonably attach conditions.
 *
 * THE ANSWER IS THEREFORE AN IMPORTER, NOT A BUNDLE.
 *
 * A.63 draws exactly this line: "Concept identifiers and mappings may be
 * bundled where legally permitted. Symbol imagery requires explicit licensing
 * review." So Aetos ships *mappings* and the machinery to install artwork, and
 * a player installs the set that suits their game's licensing and their own
 * familiarity.
 *
 * Until they do, every control falls back to its text label. That remains a
 * genuine limitation, stated plainly rather than papered over. The alternative
 * -- drawing generic icons and calling them AAC symbols -- would be worse: an
 * AAC user knows a *specific* set, and an unfamiliar picture is not a hint, it
 * is noise on top of the word.
 *
 * NEVER GUESS A REPLACEMENT (A.62)
 *
 * If a pack has no symbol for a concept, the answer is the text label. Not a
 * similar symbol, not a symbol for a related concept, not a generic placeholder
 * that means "something goes here".
 *
 * The reason is specific to AAC rather than general tidiness: a symbol
 * *is* the word for somebody using one. Substituting a near-miss is
 * substituting a different word, and the player has no way to know it happened
 * -- they would simply have said something they did not mean.
 *
 * SYMBOL PLUS TEXT (A.64)
 *
 * Controls show both by default. A symbol-only presentation is available for
 * players who want it, but it is a choice they make rather than the default,
 * because a symbol nobody recognises with no word under it is unusable while
 * the reverse is merely plain.
 */

(function (window) {
    "use strict";

    //: Bounded, because a pack is imported from a file the player supplies.
    var MAX_PACK_ENTRIES = 2000;

    /*
     * Whether a symbol source is safe to put in an `img src`.
     *
     * The same allowlist reasoning as media (M18): a pack is a file from
     * somewhere, `javascript:` in a `src` runs with the client's full
     * privileges, and a denylist would have to anticipate every scheme a
     * browser has ever supported.
     *
     * `data:` is permitted here, unlike media, and the difference is real: a
     * symbol pack is a small self-contained set of images a player has chosen
     * to install, and inlining them is how such a pack travels as one file. A
     * pack that could only reference a server would be a pack that stops
     * working offline.
     *
     * It is also the more private option, and for this widget that matters
     * more than usual. A pack of remote URLs tells whoever hosts them, every
     * time the board renders, that this browser is loading a communication
     * board -- which is a disclosure about disability, made silently, to a
     * third party the player never chose to tell. Self-contained packs make no
     * requests at all, so `packSelfContained()` exists to say which kind a
     * player has installed.
     */
    function isSafeSource(value) {
        if (typeof value !== "string" || !value) {
            return false;
        }
        var candidate = value.trim();
        if (candidate.indexOf("\\") !== -1) {
            return false;
        }
        if (/^data:image\/(png|jpeg|gif|svg\+xml|webp);base64,[A-Za-z0-9+/=]+$/.test(candidate)) {
            return true;
        }
        return /^(https?:)?\/\//.test(candidate) || candidate.charAt(0) === "/" ||
            /^[\w.-]+\//.test(candidate);
    }

    function createProvider(services) {
        var settings = services || {};
        var preferences = settings.preferences || null;

        //: Registered packs, by id.
        var packs = {};
        var activePackId = null;

        /*
         * Register a symbol pack.
         *
         * A pack declares its licence and attribution, and both are carried
         * through to every symbol it supplies. Not for form's sake: a player
         * showing somebody their board, or a developer shipping a game with a
         * pack installed, needs to be able to answer "where did these come
         * from" without going back to whoever sent them the file.
         */
        function registerPack(pack) {
            if (!pack || !pack.id || typeof pack.symbols !== "object") {
                throw new Error("A symbol pack needs an id and a symbols map.");
            }
            if (!pack.license) {
                /*
                 * Refused rather than defaulted.
                 *
                 * A pack with no stated licence is one nobody can safely pass
                 * on, and a default of "unknown" would let it spread anyway
                 * with the question quietly settled in the worst direction.
                 */
                throw new Error(
                    "A symbol pack must state its licence. Aetos will not install " +
                    "artwork whose redistribution terms are unknown."
                );
            }
            var symbols = {};
            var count = 0;
            Object.keys(pack.symbols).forEach(function (conceptId) {
                if (count >= MAX_PACK_ENTRIES) {
                    return;
                }
                var entry = pack.symbols[conceptId];
                var source = typeof entry === "string" ? entry : (entry && entry.src);
                if (!isSafeSource(source)) {
                    return;
                }
                symbols[conceptId] = {
                    src: String(source).trim(),
                    // A pack may supply its own wording for a symbol. It is
                    // used as the image's alternative text, never instead of
                    // the concept's label -- the label is what the player is
                    // choosing, and it must not change depending on which pack
                    // is installed.
                    alt: (entry && entry.alt) ? String(entry.alt) : null
                };
                count += 1;
            });
            packs[pack.id] = {
                id: String(pack.id),
                name: String(pack.name || pack.id),
                license: String(pack.license),
                attribution: pack.attribution ? String(pack.attribution) : null,
                /*
                 * Whether this pack can render without asking anybody for
                 * anything. See `isSafeSource` -- a pack of remote URLs
                 * discloses to its host that this browser is showing a
                 * communication board, which is a statement about disability
                 * made silently to a third party.
                 */
                selfContained: Object.keys(symbols).every(function (id) {
                    return symbols[id].src.indexOf("data:") === 0;
                }),
                symbols: symbols
            };
            return pack.id;
        }

        function usePack(id) {
            activePackId = packs[id] ? id : null;
            if (preferences) {
                preferences.update({ aac: { symbolPack: activePackId } });
            }
            return activePackId;
        }

        /*
         * The symbol for a concept, or null.
         *
         * Null is a complete and correct answer. The caller shows the label,
         * which is what a concept always has.
         */
        function getSymbol(concept) {
            if (!concept || !activePackId) {
                return null;
            }
            var pack = packs[activePackId];
            var found = pack && pack.symbols[concept.id];
            if (!found) {
                // No substitution, no nearest match, no placeholder. See the
                // header: a near-miss symbol is a different word.
                return null;
            }
            return {
                src: found.src,
                // Falls back to the concept's own label, so an image always has
                // an accessible name even when a pack supplies no wording.
                alt: found.alt || concept.label,
                license: pack.license,
                attribution: pack.attribution
            };
        }

        /*
         * Install a pack from a file the player chose.
         *
         * The same shape as the M5 profile importer: a local file, parsed
         * here, never fetched from anywhere. Aetos does not download symbol
         * sets on a player's behalf -- which set is appropriate depends on the
         * game's licensing and on which symbols that person already knows, and
         * neither is Aetos's decision to make.
         *
         * Reports what it refused as well as what it took. An import that
         * silently drops half a pack is worse than one that fails, because the
         * board then has holes the player will discover one word at a time.
         */
        function importPack(text) {
            var parsed;
            try {
                parsed = JSON.parse(text);
            } catch (err) {
                return { ok: false, error: "That file is not valid JSON." };
            }
            if (!parsed || typeof parsed !== "object" || !parsed.symbols) {
                return { ok: false, error: "That file is not a symbol pack." };
            }

            var offered = Object.keys(parsed.symbols || {}).length;
            var id;
            try {
                id = registerPack(parsed);
            } catch (err) {
                return { ok: false, error: err.message };
            }
            var accepted = Object.keys(packs[id].symbols).length;

            return {
                ok: true,
                id: id,
                name: packs[id].name,
                license: packs[id].license,
                accepted: accepted,
                // Refused for an unusable source: not a hex-safe URL, or past
                // the entry cap.
                refused: offered - accepted,
                selfContained: packs[id].selfContained
            };
        }

        /*
         * Which concepts a pack cannot illustrate.
         *
         * Surfaced rather than discovered a word at a time. A pack covering
         * everything except `yes`, `no` and `stop` is a specific and
         * predictable failure -- it is what happens with a vocabulary set
         * rather than a core board -- and a player deserves to see that before
         * they rely on it mid-conversation.
         */
        function missingConcepts() {
            var pack = activePack();
            if (!pack || !window.AetosConcepts) {
                return [];
            }
            return window.AetosConcepts.CONCEPTS.filter(function (concept) {
                return !pack.symbols[concept.id];
            }).map(function (concept) { return concept.label; });
        }

        function activePack() {
            return activePackId ? packs[activePackId] : null;
        }

        function allPacks() {
            return Object.keys(packs).map(function (id) {
                return {
                    id: id,
                    name: packs[id].name,
                    license: packs[id].license,
                    attribution: packs[id].attribution,
                    count: Object.keys(packs[id].symbols).length
                };
            });
        }

        return {
            registerPack: registerPack,
            importPack: importPack,
            missingConcepts: missingConcepts,
            packSelfContained: function () {
                var pack = activePack();
                return pack ? pack.selfContained : null;
            },
            usePack: usePack,
            getSymbol: getSymbol,
            activePack: activePack,
            allPacks: allPacks,
            isSafeSource: isSafeSource
        };
    }

    window.AetosSymbolProvider = {
        create: createProvider,
        isSafeSource: isSafeSource,
        MAX_PACK_ENTRIES: MAX_PACK_ENTRIES
    };

})(window);
