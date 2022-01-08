# Red Button example

Contribution by Griatch, 2011

A red button that you can press to have an effect. This is a more advanced example 
object with its own functionality and state tracking.

Create the button with

    create/drop button:tutorials.red_button.RedButton

Note that you must drop the button before you can see its messages! It's
imperative that you press the red button. You know you want to.

Use `del button` to destroy/stop the button when you are done playing.

## Technical

The button's functionality is controlled by CmdSets that gets added and removed
depending on the 'state' the button is in.

- Lid-closed state: In this state the button is covered by a glass cover and
  trying to 'push' it will fail. You can 'nudge', 'smash' or 'open' the lid.
- Lid-open state: In this state the lid is open but will close again after a
  certain time. Using 'push' now will press the button and trigger the
  Blind-state.
- Blind-state: In this mode you are blinded by a bright flash. This will affect
  your normal commands like 'look' and help until the blindness wears off after
  a certain time.

Timers are handled by persistent delays on the button. These are examples of
`evennia.utils.utils.delay` calls that wait a certain time before calling a
method - such as when closing the lid and un-blinding a character.

