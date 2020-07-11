# Bootstrap & Evennia

# What is Bootstrap?
Evennia's new default web page uses a framework called [Bootstrap](https://getbootstrap.com/). This
framework is in use across the internet - you'll probably start to recognize its influence once you
learn some of the common design patterns. This switch is great for web developers, perhaps like
yourself, because instead of wondering about setting up different grid systems or what custom class
another designer used, we have a base, a bootstrap, to work from. Bootstrap is responsive by
default, and comes with some default styles that Evennia has lightly overrode to keep some of the
same colors and styles you're used to from the previous design.

For your reading pleasure, a brief overview of Bootstrap follows. For more in-depth info, please
read [the documentation](https://getbootstrap.com/docs/4.0/getting-started/introduction/).
***

## The Layout System
Other than the basic styling Bootstrap includes, it also includes [a built in layout and grid
system](https://getbootstrap.com/docs/4.0/layout/overview/).
The first part of this system is [the
container](https://getbootstrap.com/docs/4.0/layout/overview/#containers).

The container is meant to hold all your page content. Bootstrap provides two types: fixed-width and
full-width.
Fixed-width containers take up a certain max-width of the page - they're useful for limiting the
width on Desktop or Tablet platforms, instead of making the content span the width of the page.
```
<div class="container">
    <!--- Your content here -->
</div>
```
Full width containers take up the maximum width available to them - they'll span across a wide-
screen desktop or a smaller screen phone, edge-to-edge.
```
<div class="container-fluid">
    <!--- This content will span the whole page -->
</div>
```

The second part of the layout system is [the grid](https://getbootstrap.com/docs/4.0/layout/grid/).
This is the bread-and-butter of the layout of Bootstrap - it allows you to change the size of
elements depending on the size of the screen, without writing any media queries. We'll briefly go
over it - to learn more, please read the docs or look at the source code for Evennia's home page in
your browser.
> Important! Grid elements should be in a .container or .container-fluid. This will center the
contents of your site.

Bootstrap's grid system allows you to create rows and columns by applying classes based on
breakpoints. The default breakpoints are extra small, small, medium, large, and extra-large. If
you'd like to know more about these breakpoints, please [take a look at the documentation for
them.](https://getbootstrap.com/docs/4.0/layout/overview/#responsive-breakpoints)

To use the grid system, first create a container for your content, then add your rows and columns
like so:
```
<div class="container">
    <div class="row">
        <div class="col">
           1 of 3
        </div>
        <div class="col">
           2 of 3
        </div>
        <div class="col">
           3 of 3
        </div>
    </div>
</div>
```
This layout would create three equal-width columns.

To specify your sizes - for instance, Evennia's default site has three columns on desktop and
tablet, but reflows to single-column on smaller screens. Try it out!
```
<div class="container">
    <div class="row">
        <div class="col col-md-6 col-lg-3">
            1 of 4
        </div>
        <div class="col col-md-6 col-lg-3">
            2 of 4
        </div>
        <div class="col col-md-6 col-lg-3">
            3 of 4
        </div>
        <div class="col col-md-6 col-lg-3">
            4 of 4
        </div>
    </div>
</div>
```
This layout would be 4 columns on large screens, 2 columns on medium screens, and 1 column on
anything smaller.

To learn more about Bootstrap's grid, please [take a look at the
docs](https://getbootstrap.com/docs/4.0/layout/grid/)
***

## More Bootstrap
Bootstrap also provides a huge amount of utilities, as well as styling and content elements. To
learn more about them, please [read the Bootstrap docs](https://getbootstrap.com/docs/4.0/getting-
started/introduction/) or read one of our other web tutorials.