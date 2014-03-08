from ev import default_cmds

class MuxCommand(default_cmds.MuxCommand):
    """
    This sets up the basis for a Evennia's 'MUX-like' command
    style. The idea is that most other Mux-related commands should
    just inherit from this and don't have to implement parsing of
    their own unless they do something particularly advanced.

    A MUXCommand command understands the following possible syntax:

      name[ with several words][/switch[/switch..]] arg1[,arg2,...] [[=|,] arg[,..]]

    The 'name[ with several words]' part is already dealt with by the
    cmdhandler at this point, and stored in self.cmdname. The rest is stored
    in self.args.

    The MuxCommand parser breaks self.args into its constituents and stores them in the
    following variables:
      self.switches = optional list of /switches (without the /)
      self.raw = This is the raw argument input, including switches
      self.args = This is re-defined to be everything *except* the switches
      self.lhs = Everything to the left of = (lhs:'left-hand side'). If
                 no = is found, this is identical to self.args.
      self.rhs: Everything to the right of = (rhs:'right-hand side').
                If no '=' is found, this is None.
      self.lhslist - self.lhs split into a list by comma
      self.rhslist - list of self.rhs split into a list by comma
      self.arglist = list of space-separated args (including '=' if it exists)

      All args and list members are stripped of excess whitespace around the
      strings, but case is preserved.
      """

    def partial(self,a,b):
        if not isinstance(a,list): a = list(a)
        if not isinstance(b,list): b = list(b)
        b = list(b)
        alower = []
        for element in a:
            alower.append(element.lower())
        blower = []
        for element in b:
            blower.append(element.lower())
        c = []
        for item in blower:
            if item in alower:
                c.append(item)
                alower = [x for x in alower if x != item]
            for entry in alower:
                if item.startswith(entry):
                    c.append(item)
                    alower.remove(entry)
                else:
                    c.append(entry)
        c = list(set(c))
        c.sort()
        return c

    def parse(self):
        super(MuxCommand, self).parse()
        if hasattr(self.caller,"player"):
            self.player = self.caller.player
            self.character = self.caller
            self.isic = True
        else:
            self.player = self.caller
            self.isic = False
        self.isadmin = self.caller.locks.check_lockstring(self.caller, "dummy:perm(Wizards)")
        
    def func(self):
        """
        This is the hook function that actually does all the work. It is called
        by the cmdhandler right after self.parser() finishes, and so has access
        to all the variables defined therein.
        """
        # this can be removed in your child class, it's just
        # printing the ingoing variables as a demo.
        super(MuxCommand, self).func()

