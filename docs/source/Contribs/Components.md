# Components

_Contrib by ChrisLR 2021_

# The Components Contrib

This contrib allows you to develop your mud with more composition and less inheritance.
This is not a true ECS system built-in, as each components will likely need
to know about each other instead of using dynamic messages.

Why would you want to do this?
It allows you to keep your code clean and focused to one feature at a time.

For example, a 'health' component which contains the current and max health
but also the damage/heals method and various logic about dying.
Then all you have to do is give this component to any object that can be damaged.
After that you could filter any targets for the presence of the .health component

if not target.health:
    return "You cannot attack this!"
else:
    damage = roll_damage()
    target.damage(damage)

Another advantage is runtime components, allowing you to give and remove
components to your objects to extend them at any time.

