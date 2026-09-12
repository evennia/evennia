/*
 * Aetos Script -- a small, deliberately weak language.
 *
 * Blueprint section 33 forbids evaluating arbitrary JavaScript. So this is a
 * real tokenizer, parser and tree-walking interpreter for a language that
 * cannot express anything dangerous, rather than a sandbox bolted around
 * `eval` and hoped over.
 *
 * WHY NOT eval, OR Function, OR A WORKER?
 *
 *   - `eval` and `new Function` hand the script the whole JavaScript runtime.
 *     Every escape from such a sandbox in the wild has come from a reference
 *     leaking through -- a constructor, a prototype, an error object -- and
 *     auditing for that is a losing game.
 *   - A Web Worker isolates the DOM but still grants `fetch`, `WebSocket` and
 *     `importScripts`, which is exactly the network reach section 33 forbids.
 *
 * A script here can only do what the interpreter implements. There is no
 * property access, no indexing, no function definition, no way to name a host
 * object. The only callable things are the API functions the host injects.
 *
 * WHAT A SCRIPT CAN DO
 *
 *   send("north")            queue an ordinary command
 *   echo("text")             write to the player's own console
 *   resource("health")       read a resource, 0..1 when bounded
 *   room()                   current room name
 *   target()                 current target name
 *   get("key") / set("key", value)   the script's own variables
 *
 * Every one of those is a function the host supplies. Remove it from the API
 * and the script simply cannot refer to it.
 *
 * BUDGETS
 *
 * A halting oracle is not available, so the interpreter counts. Steps, loop
 * iterations, call depth, string length and wall-clock time are all bounded,
 * and exceeding any of them stops the script with an explanation rather than
 * freezing the player's browser.
 */

(function (window) {
    "use strict";

    var MAX_STEPS = 10000;
    var MAX_LOOP_ITERATIONS = 1000;
    var MAX_CALL_DEPTH = 16;
    var MAX_STRING_LENGTH = 2000;
    var MAX_RUNTIME_MS = 250;
    var MAX_SOURCE_LENGTH = 20000;

    /* ==================================================================
     * Tokenizer
     * ================================================================== */

    var KEYWORDS = ["if", "then", "else", "end", "while", "do", "set",
                    "and", "or", "not", "true", "false"];

    function tokenize(source) {
        var tokens = [];
        var i = 0;
        var line = 1;
        var text = String(source || "");

        if (text.length > MAX_SOURCE_LENGTH) {
            throw new Error("Script is too long.");
        }

        function push(type, value) {
            tokens.push({ type: type, value: value, line: line });
        }

        while (i < text.length) {
            var ch = text[i];

            if (ch === "\n") {
                line += 1;
                i += 1;
                continue;
            }
            if (/\s/.test(ch)) {
                i += 1;
                continue;
            }
            // Comments run to end of line.
            if (ch === "#") {
                while (i < text.length && text[i] !== "\n") {
                    i += 1;
                }
                continue;
            }

            if (ch === '"' || ch === "'") {
                var quote = ch;
                var value = "";
                i += 1;
                while (i < text.length && text[i] !== quote) {
                    // No escape sequences beyond \\ and the quote itself: a
                    // richer escape syntax buys nothing here and adds parsing
                    // surface.
                    if (text[i] === "\\" && i + 1 < text.length) {
                        i += 1;
                    }
                    value += text[i];
                    i += 1;
                    if (value.length > MAX_STRING_LENGTH) {
                        throw new Error("String literal is too long (line " + line + ").");
                    }
                }
                if (i >= text.length) {
                    throw new Error("Unterminated string (line " + line + ").");
                }
                i += 1;
                push("string", value);
                continue;
            }

            if (/[0-9]/.test(ch)) {
                var number = "";
                while (i < text.length && /[0-9.]/.test(text[i])) {
                    number += text[i];
                    i += 1;
                }
                var parsed = parseFloat(number);
                if (!isFinite(parsed)) {
                    throw new Error("Bad number " + number + " (line " + line + ").");
                }
                push("number", parsed);
                continue;
            }

            if (/[A-Za-z_]/.test(ch)) {
                var word = "";
                while (i < text.length && /[A-Za-z0-9_]/.test(text[i])) {
                    word += text[i];
                    i += 1;
                }
                push(KEYWORDS.indexOf(word) !== -1 ? word : "name", word);
                continue;
            }

            var two = text.substr(i, 2);
            if (["==", "!=", "<=", ">="].indexOf(two) !== -1) {
                push("op", two);
                i += 2;
                continue;
            }
            if ("+-*/%<>=(),".indexOf(ch) !== -1) {
                push(ch === "(" || ch === ")" || ch === "," ? ch : "op", ch);
                i += 1;
                continue;
            }

            throw new Error("Unexpected character " + JSON.stringify(ch) +
                " (line " + line + ").");
        }

        push("eof", null);
        return tokens;
    }

    /* ==================================================================
     * Parser
     *
     * Produces a plain-object AST. Nothing in the tree is executable on its
     * own -- the interpreter decides what each node means.
     * ================================================================== */

    function parse(tokens) {
        var pos = 0;

        function peek() { return tokens[pos]; }
        function next() { return tokens[pos++]; }

        function expect(type, value) {
            var token = next();
            if (token.type !== type || (value !== undefined && token.value !== value)) {
                throw new Error(
                    "Expected " + (value || type) + " but found " +
                    (token.value === null ? "end of script" : token.value) +
                    " (line " + token.line + ").");
            }
            return token;
        }

        function parseBlock(terminators) {
            var statements = [];
            while (peek().type !== "eof" && terminators.indexOf(peek().type) === -1) {
                statements.push(parseStatement());
            }
            return { type: "block", body: statements };
        }

        function parseStatement() {
            var token = peek();

            if (token.type === "set") {
                next();
                var name = expect("name").value;
                expect("op", "=");
                return { type: "assign", name: name, value: parseExpression(), line: token.line };
            }

            if (token.type === "if") {
                next();
                var condition = parseExpression();
                expect("then");
                var consequent = parseBlock(["else", "end"]);
                var alternate = null;
                if (peek().type === "else") {
                    next();
                    alternate = parseBlock(["end"]);
                }
                expect("end");
                return {
                    type: "if", condition: condition,
                    consequent: consequent, alternate: alternate, line: token.line
                };
            }

            if (token.type === "while") {
                next();
                var test = parseExpression();
                expect("do");
                var body = parseBlock(["end"]);
                expect("end");
                return { type: "while", test: test, body: body, line: token.line };
            }

            return { type: "expression", value: parseExpression(), line: token.line };
        }

        // Precedence climbing, loosest first.
        function parseExpression() { return parseOr(); }

        function parseOr() {
            var left = parseAnd();
            while (peek().type === "or") {
                next();
                left = { type: "logical", op: "or", left: left, right: parseAnd() };
            }
            return left;
        }

        function parseAnd() {
            var left = parseComparison();
            while (peek().type === "and") {
                next();
                left = { type: "logical", op: "and", left: left, right: parseComparison() };
            }
            return left;
        }

        function parseComparison() {
            var left = parseAdditive();
            while (peek().type === "op" &&
                    ["==", "!=", "<", "<=", ">", ">="].indexOf(peek().value) !== -1) {
                var op = next().value;
                left = { type: "binary", op: op, left: left, right: parseAdditive() };
            }
            return left;
        }

        function parseAdditive() {
            var left = parseMultiplicative();
            while (peek().type === "op" && ["+", "-"].indexOf(peek().value) !== -1) {
                var op = next().value;
                left = { type: "binary", op: op, left: left, right: parseMultiplicative() };
            }
            return left;
        }

        function parseMultiplicative() {
            var left = parseUnary();
            while (peek().type === "op" && ["*", "/", "%"].indexOf(peek().value) !== -1) {
                var op = next().value;
                left = { type: "binary", op: op, left: left, right: parseUnary() };
            }
            return left;
        }

        function parseUnary() {
            if (peek().type === "not") {
                next();
                return { type: "unary", op: "not", value: parseUnary() };
            }
            if (peek().type === "op" && peek().value === "-") {
                next();
                return { type: "unary", op: "-", value: parseUnary() };
            }
            return parsePrimary();
        }

        function parsePrimary() {
            var token = next();

            if (token.type === "number") { return { type: "literal", value: token.value }; }
            if (token.type === "string") { return { type: "literal", value: token.value }; }
            if (token.type === "true") { return { type: "literal", value: true }; }
            if (token.type === "false") { return { type: "literal", value: false }; }

            if (token.type === "(") {
                var inner = parseExpression();
                expect(")");
                return inner;
            }

            if (token.type === "name") {
                if (peek().type === "(") {
                    next();
                    var args = [];
                    if (peek().type !== ")") {
                        args.push(parseExpression());
                        while (peek().type === ",") {
                            next();
                            args.push(parseExpression());
                        }
                    }
                    expect(")");
                    // A call names a function in the API by string. There is no
                    // way to obtain a function value, so nothing else is
                    // callable.
                    return { type: "call", name: token.value, args: args, line: token.line };
                }
                return { type: "variable", name: token.value, line: token.line };
            }

            throw new Error("Unexpected " +
                (token.value === null ? "end of script" : token.value) +
                " (line " + token.line + ").");
        }

        var program = parseBlock([]);
        expect("eof");
        return program;
    }

    /* ==================================================================
     * Interpreter
     * ================================================================== */

    function createInterpreter(api, options) {
        var opts = options || {};
        var now = opts.now || function () { return Date.now(); };

        function run(program, initialVariables) {
            var variables = {};
            Object.keys(initialVariables || {}).forEach(function (key) {
                variables[key] = initialVariables[key];
            });

            var steps = 0;
            var depth = 0;
            var started = now();
            var output = [];

            function step(line) {
                steps += 1;
                if (steps > MAX_STEPS) {
                    throw new Error("Script did too much work and was stopped" +
                        (line ? " (line " + line + ")" : "") + ".");
                }
                // Wall clock as well as steps: a script can be slow without
                // being long, and the browser must stay responsive.
                if (steps % 200 === 0 && now() - started > MAX_RUNTIME_MS) {
                    throw new Error("Script ran too long and was stopped.");
                }
            }

            function truthy(value) {
                return !(value === false || value === 0 || value === "" ||
                         value === null || value === undefined);
            }

            function evaluate(node) {
                step(node.line);

                switch (node.type) {
                case "literal":
                    return node.value;

                case "variable":
                    // An unset variable reads as false rather than throwing: a
                    // script checking a value it has not set yet is ordinary.
                    return Object.prototype.hasOwnProperty.call(variables, node.name)
                        ? variables[node.name]
                        : false;

                case "unary":
                    if (node.op === "not") {
                        return !truthy(evaluate(node.value));
                    }
                    return -Number(evaluate(node.value));

                case "logical":
                    var leftValue = evaluate(node.left);
                    if (node.op === "and") {
                        return truthy(leftValue) ? evaluate(node.right) : leftValue;
                    }
                    return truthy(leftValue) ? leftValue : evaluate(node.right);

                case "binary":
                    return applyBinary(node.op, evaluate(node.left), evaluate(node.right));

                case "call":
                    return callFunction(node);

                default:
                    throw new Error("Cannot evaluate " + node.type + ".");
                }
            }

            function applyBinary(op, left, right) {
                switch (op) {
                case "+":
                    // String concatenation is useful for echo(); bound it so a
                    // loop cannot build a giant string.
                    if (typeof left === "string" || typeof right === "string") {
                        var joined = String(left) + String(right);
                        if (joined.length > MAX_STRING_LENGTH) {
                            throw new Error("Script built too large a string.");
                        }
                        return joined;
                    }
                    return Number(left) + Number(right);
                case "-": return Number(left) - Number(right);
                case "*": return Number(left) * Number(right);
                case "/":
                    if (Number(right) === 0) {
                        throw new Error("Division by zero.");
                    }
                    return Number(left) / Number(right);
                case "%":
                    if (Number(right) === 0) {
                        throw new Error("Division by zero.");
                    }
                    return Number(left) % Number(right);
                case "==": return left === right;
                case "!=": return left !== right;
                case "<": return Number(left) < Number(right);
                case "<=": return Number(left) <= Number(right);
                case ">": return Number(left) > Number(right);
                case ">=": return Number(left) >= Number(right);
                default:
                    throw new Error("Unknown operator " + op + ".");
                }
            }

            function callFunction(node) {
                depth += 1;
                if (depth > MAX_CALL_DEPTH) {
                    throw new Error("Script nested calls too deeply.");
                }
                try {
                    // The ONLY way to call anything. `api` is a plain object the
                    // host built; a name not in it does not exist as far as the
                    // script is concerned.
                    if (!Object.prototype.hasOwnProperty.call(api, node.name)) {
                        throw new Error("There is no function called " + node.name +
                            " (line " + node.line + ").");
                    }
                    var args = node.args.map(evaluate);
                    var result = api[node.name].apply(null, args);
                    if (result && typeof result === "object") {
                        // Never let a host object into script space. Returning
                        // one would give the script a reference it could not
                        // otherwise obtain.
                        return String(result);
                    }
                    return result === undefined ? false : result;
                } finally {
                    depth -= 1;
                }
            }

            function execute(node) {
                step(node.line);

                switch (node.type) {
                case "block":
                    node.body.forEach(execute);
                    return;

                case "assign":
                    variables[node.name] = evaluate(node.value);
                    return;

                case "if":
                    if (truthy(evaluate(node.condition))) {
                        execute(node.consequent);
                    } else if (node.alternate) {
                        execute(node.alternate);
                    }
                    return;

                case "while":
                    var iterations = 0;
                    while (truthy(evaluate(node.test))) {
                        iterations += 1;
                        if (iterations > MAX_LOOP_ITERATIONS) {
                            throw new Error("Loop ran too many times and was stopped" +
                                " (line " + node.line + ").");
                        }
                        execute(node.body);
                    }
                    return;

                case "expression":
                    evaluate(node.value);
                    return;

                default:
                    throw new Error("Cannot execute " + node.type + ".");
                }
            }

            execute(program);
            return { variables: variables, steps: steps, output: output };
        }

        return { run: run };
    }

    /* ==================================================================
     * Public surface
     * ================================================================== */

    function compile(source) {
        return parse(tokenize(source));
    }

    function createScripting(services) {
        var storage = services.storage;
        var isAllowed = services.isAllowed || function () { return false; };
        var announce = services.announce || function () {};
        var api = services.api || {};

        var interpreter = createInterpreter(api, { now: services.now });

        function save(script) {
            if (!storage) {
                return window.Promise.resolve(null);
            }
            var record = {
                id: script.id || String(script.label || "script").toLowerCase(),
                label: String(script.label || "Script").slice(0, 80),
                source: String(script.source || "").slice(0, MAX_SOURCE_LENGTH),
                enabled: script.enabled !== false
            };
            // Compile on save so a syntax error is reported once, here, rather
            // than every time the script is meant to run.
            try {
                compile(record.source);
            } catch (err) {
                return window.Promise.reject(err);
            }
            return storage.put("scripts", record.id, record).then(function () {
                return record;
            });
        }

        function all() {
            if (!storage) {
                return window.Promise.resolve([]);
            }
            return storage.all("scripts").then(function (rows) {
                return rows.map(function (row) { return row.value; });
            });
        }

        function remove(id) {
            return storage ? storage.remove("scripts", id) : window.Promise.resolve(false);
        }

        /*
         * Run a script.
         *
         * Returns a report rather than throwing: a script stopping is a normal
         * event the player should be told about, not an exception the client
         * has to survive.
         */
        function run(source, variables) {
            if (!isAllowed()) {
                announce("This game does not allow scripting.");
                return { ok: false, error: "scripting disabled" };
            }
            var program;
            try {
                program = compile(source);
            } catch (err) {
                announce("Script error: " + err.message);
                return { ok: false, error: err.message };
            }
            try {
                var result = interpreter.run(program, variables);
                return { ok: true, variables: result.variables, steps: result.steps };
            } catch (err) {
                announce("Script stopped: " + err.message);
                return { ok: false, error: err.message };
            }
        }

        return {
            compile: compile,
            save: save,
            all: all,
            remove: remove,
            run: run
        };
    }

    window.AetosScripting = {
        create: createScripting,
        compile: compile,
        tokenize: tokenize,
        parse: parse,
        createInterpreter: createInterpreter,
        LIMITS: {
            MAX_STEPS: MAX_STEPS,
            MAX_LOOP_ITERATIONS: MAX_LOOP_ITERATIONS,
            MAX_CALL_DEPTH: MAX_CALL_DEPTH,
            MAX_STRING_LENGTH: MAX_STRING_LENGTH,
            MAX_RUNTIME_MS: MAX_RUNTIME_MS,
            MAX_SOURCE_LENGTH: MAX_SOURCE_LENGTH
        }
    };

})(window);
