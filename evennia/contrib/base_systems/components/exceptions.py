class InvalidComponentError(ValueError):
    pass


class ComponentDoesNotExist(ValueError):
    pass


class ComponentIsNotRegistered(ValueError):
    pass


class ComponentSlotRegisteredTwice(ValueError):
    pass
