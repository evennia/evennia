"""
`evennia aetos <subcommand>` -- the one canonical Aetos command.

WHY THIS WORKS WITHOUT TOUCHING THE LAUNCHER, which was D0's open question.

Evennia's launcher has a fixed list of operations it handles itself. Anything
else falls through to Django's management-command dispatch with the original
command line intact, so a management command named `aetos` in an installed app
*is* `evennia aetos`. Aetos is already an installed app -- it has to be, or its
templates and static files are not found -- so this needs no settings entry, no
`EXTRA_LAUNCHER_COMMANDS`, and no change to Evennia.

Verified rather than assumed: `evennia aetos discover` was run against the lab
game before any of this was designed around it.

There is one trap worth recording for whoever reads the launcher next.
`run_custom_commands` is a real extension hook, but its docstring names the
setting `CUSTOM_EVENNIA_LAUNCHER_COMMANDS` while the code reads
`EXTRA_LAUNCHER_COMMANDS`. Following the documentation gets you nothing, and it
fails *silently*: the missing attribute is caught, the hook returns False, and
the command falls through to Django, which reports an unrelated "unknown
command". Not the route taken here, and worth knowing before somebody spends an
hour on it.

ONE COMMAND, SUBCOMMANDS UNDERNEATH. Addendum B.34 asks the documentation to
expose exactly one command, and this is it. `discover` is the only subcommand
D0 ships; D1 and D2 add to this file rather than adding commands beside it.

"""

from django.core.management.base import BaseCommand, CommandError

SUBCOMMANDS = ("discover", "setup")


class Command(BaseCommand):
    """The Aetos developer command."""

    help = (
        "Aetos web client developer tools. "
        "`evennia aetos discover` suggests AETOS_BINDINGS from your game's own data; "
        "`evennia aetos setup` walks through those suggestions one at a time, tests "
        "each against a live character, and writes what you accept to aetos-discovery/."
    )

    def add_arguments(self, parser):
        """
        Declare the command line.

        Args:
            parser (ArgumentParser): Django's parser for this command.

        """
        parser.add_argument(
            "subcommand",
            nargs="?",
            default="",
            help="One of: %s" % ", ".join(SUBCOMMANDS),
        )
        parser.add_argument(
            "--all",
            action="store_true",
            dest="include_all",
            default=False,
            help=(
                "Include attributes discovery normally filters out as bookkeeping. "
                "The filter is a guess, so this is here for when it guesses wrong."
            ),
        )
        parser.add_argument(
            "--character",
            default=None,
            help=(
                "The representative character to read, as #12 or a name. Worth "
                "naming one: a character mid-way through the game carries what a "
                "fresh one does not. Without it, the newest characters are sampled."
            ),
        )
        parser.add_argument(
            "--typeclass",
            default=None,
            help=(
                "Sample characters of this typeclass (and its subclasses) instead "
                "of BASE_CHARACTER_TYPECLASS."
            ),
        )
        parser.add_argument(
            "--static-only",
            action="store_true",
            default=False,
            help="Read only the typeclass source, not the database.",
        )
        parser.add_argument(
            "--runtime-only",
            action="store_true",
            default=False,
            help="Read only existing characters, not the source.",
        )

    def handle(self, *args, **options):
        """
        Run the requested subcommand.

        Args:
            *args: Unused.
            **options: Parsed arguments.

        Raises:
            CommandError: If the subcommand is missing or unknown. Named
                explicitly rather than defaulting to `discover`, because a
                command that does something when you have not said what to do is
                a command people run by accident.

        """
        subcommand = options.get("subcommand") or ""

        if not subcommand:
            self.stdout.write(self.help)
            self.stdout.write("")
            self.stdout.write("Subcommands: %s" % ", ".join(SUBCOMMANDS))
            return

        if subcommand not in SUBCOMMANDS:
            raise CommandError(
                "unknown Aetos subcommand %r. Available: %s" % (subcommand, ", ".join(SUBCOMMANDS))
            )

        if subcommand == "setup":
            self._setup(options)
        else:
            self._discover(options)

    def _gather(self, options):
        """
        Run whichever scans the options ask for.

        Args:
            options (dict): Parsed arguments.

        Returns:
            tuple: `(CandidateSet, problems, context, characters)`.

        Raises:
            CommandError: If a scan root escapes the game, or the developer
                named a character or typeclass that cannot be used.

        """
        # Imported here rather than at module level so that `evennia aetos` with
        # no subcommand -- and Django's own command discovery, which imports
        # every command module it finds -- does not pay for a database query or
        # a source walk.
        from datetime import datetime

        from django.conf import settings

        import evennia

        # The launcher calls this itself whenever the database exists -- it is
        # what `evennia shell` gets -- but not before handing a command to
        # Django. Without it the flat API (`evennia.default_cmds` and the rest)
        # is still None, so a game's command set module fails to import and
        # Evennia quietly substitutes an empty error set: discovery then reports
        # a game with commands as having none. It builds the API and starts
        # nothing -- no service, no port, no reactor. Idempotent.
        evennia._init()

        from evennia.contrib.base_systems.aetos_webclient.discovery import (
            CandidateSet,
            ScanRootError,
            runtime_scan,
            static_scan,
            structure,
        )

        found = CandidateSet()
        problems = []
        characters = []
        context = {
            "gamedir": getattr(settings, "GAME_DIR", ""),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }

        if not options.get("runtime_only"):
            try:
                candidates, actions, issues = static_scan.scan_files(stats=context)
            except ScanRootError as error:
                raise CommandError(str(error))
            for candidate in candidates:
                found.add(candidate)
            for action in actions:
                found.add_action(action)
            problems.extend(issues)

        if not options.get("static_only"):
            try:
                characters = runtime_scan.select_characters(
                    character=options.get("character"), typeclass=options.get("typeclass")
                )
            except runtime_scan.SelectionError as error:
                raise CommandError(str(error))

            candidates, issues = runtime_scan.scan_characters(characters)
            for candidate in candidates:
                found.add(candidate)
            problems.extend(issues)

            # Pass 2 reads the classes and command sets of characters Pass 1
            # already fetched. With none, there is nothing loaded to read, and it
            # does not go and load a typeclass to find out.
            described = structure.inspect(characters)
            for candidate in described["candidates"]:
                found.add(candidate)
            for action in described["actions"]:
                found.add_action(action)
            problems.extend(described["problems"])
            context["lineages"] = described["lineages"]
            context["commands_from"] = described["commands_from"]

            named = [runtime_scan.describe(c) for c in characters[: runtime_scan.MAX_NAMED]]
            if len(characters) > runtime_scan.MAX_NAMED:
                named.append("and %d more" % (len(characters) - runtime_scan.MAX_NAMED))
            context["characters"] = named

        found.pair_maximums()
        found.assess(sampled=len(characters))
        context["problems"] = problems
        return found, problems, context, characters

    def _discover(self, options):
        """
        Suggest `AETOS_BINDINGS` from the game's own data.

        Args:
            options (dict): Parsed arguments.

        """
        from evennia.contrib.base_systems.aetos_webclient.discovery import report

        found, problems, context, _ = self._gather(options)
        self.stdout.write(
            report.render(
                found,
                problems=problems,
                include_all=options.get("include_all"),
                context=context,
            )
        )

    def _setup(self, options):
        """
        Walk the suggestions one at a time, test each, and write what is accepted.

        Args:
            options (dict): Parsed arguments.

        Notes:
            The wizard owns no input or output of its own; this is where it is
            wired to a terminal. Quitting, or running with no terminal at all,
            writes nothing -- the files appear only at the end of a walk the
            developer finished.

        """
        from evennia.contrib.base_systems.aetos_webclient.discovery import (
            generate,
            wizard,
        )

        found, problems, context, characters = self._gather(options)

        walk = wizard.Wizard(
            found,
            context=context,
            character=characters[0] if characters else None,
            ask=lambda prompt: input(prompt),
            say=lambda text: self.stdout.write(text),
        )
        result = walk.run()
        if result["quit"]:
            return

        accepted = result["accepted"]
        bindings = generate.bindings_source(accepted) if accepted else None
        provider = (
            generate.provider_source(result["provider_findings"])
            if result["provider_findings"]
            else None
        )
        names = [generate.REPORT_FILE]
        if bindings:
            names.append(generate.BINDINGS_FILE)
        if provider:
            names.append(generate.PROVIDER_FILE)

        text = generate.report_source(
            context,
            result["accepted_lines"],
            result["ignored_lines"],
            problems,
            names,
        )

        try:
            written = generate.write(
                context.get("gamedir"), text, bindings=bindings, provider=provider
            )
        except Exception as error:
            raise CommandError("nothing was written (%s)" % error)

        self.stdout.write("")
        self.stdout.write("Written:")
        for path in written:
            self.stdout.write("  %s" % path)
        self.stdout.write("")
        self.stdout.write(
            "Nothing has been applied. Copy what you want from %s into "
            "server/conf/settings.py." % generate.BINDINGS_FILE
        )
