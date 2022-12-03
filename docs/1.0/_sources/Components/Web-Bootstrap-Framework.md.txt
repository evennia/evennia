# Bootstrap frontend framework

Evennia's default web page uses a framework called [Bootstrap](https://getbootstrap.com/). This framework is in use across the internet - you'll probably start to recognize its influence once you learn some of the common design patterns. This switch is great for web developers, perhaps like yourself, because instead of wondering about setting up different grid systems or what custom class another designer used, we have a base, a bootstrap, to work from. Bootstrap is responsive by default, and comes with some default styles that Evennia has lightly overrode to keep some of the same colors and styles you're used to from the previous design.

e, a brief overview of Bootstrap follows. For more in-depth info, please
read [the documentation](https://getbootstrap.com/docs/4.0/getting-started/introduction/).

## Grid system

Other than the basic styling Bootstrap includes, it also includes [a built in layout and grid system](https://getbootstrap.com/docs/4.0/layout/overview/). 

### The container

The first part of the grid system is [the container](https://getbootstrap.com/docs/4.0/layout/overview/#containers).

The container is meant to hold all your page content. Bootstrap provides two types: fixed-width and
full-width. Fixed-width containers take up a certain max-width of the page - they're useful for limiting the width on Desktop or Tablet platforms, instead of making the content span the width of the page.

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

### The grid

The second part of the layout system is [the grid](https://getbootstrap.com/docs/4.0/layout/grid/).

This is the bread-and-butter of the layout of Bootstrap - it allows you to change the size of elements depending on the size of the screen, without writing any media queries. We'll briefly go over it - to learn more, please read the docs or look at the source code for Evennia's home page in your browser. 

> Important! Grid elements should be in a .container or .container-fluid. This will center the
contents of your site.

Bootstrap's grid system allows you to create rows and columns by applying classes based on breakpoints. The default breakpoints are extra small, small, medium, large, and extra-large. If you'd like to know more about these breakpoints, please [take a look at the documentation for
them.](https://getbootstrap.com/docs/4.0/layout/overview/#responsive-breakpoints)

To use the grid system, first create a container for your content, then add your rows and columns like so:
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
I
## General Styling elements

Bootstrap provides base styles for your site. These can be customized through CSS, but the default
styles are intended to provide a consistent, clean look for sites.

### Color
Most elements can be styled with default colors. [Take a look at the documentation](https://getbootstrap.com/docs/4.0/utilities/colors/) to learn more about these colors
- suffice to say, adding a class of text-* or bg-*, for instance, text-primary, sets the text color
or background color.

### Borders

Simply adding a class of 'border' to an element adds a border to the element. For more in-depth
info, please [read the documentation on borders.](https://getbootstrap.com/docs/4.0/utilities/borders/).
```
<span class="border border-dark"></span>
```
You can also easily round corners just by adding a class.
```
<img src="..." class="rounded" />
```

### Spacing
Bootstrap provides classes to easily add responsive margin and padding. Most of the time, you might like to add margins or padding through CSS itself - however these classes are used in the default Evennia site. [Take a look at the docs](https://getbootstrap.com/docs/4.0/utilities/spacing/) to
learn more.

### Buttons

[Buttons](https://getbootstrap.com/docs/4.0/components/buttons/) in Bootstrap are very easy to use - button styling can be added to `<button>`, `<a>`, and `<input>` elements.
```
<a class="btn btn-primary" href="#" role="button">I'm a Button</a>
<button class="btn btn-primary" type="submit">Me too!</button>
<input class="btn btn-primary" type="button" value="Button">
<input class="btn btn-primary" type="submit" value="Also a Button">
<input class="btn btn-primary" type="reset" value="Button as Well">
```

### Cards

[Cards](https://getbootstrap.com/docs/4.0/components/card/) provide a container for other elements
that stands out from the rest of the page. The "Accounts", "Recently Connected", and "Database
Stats" on the default webpage are all in cards. Cards provide quite a bit of formatting options -
the following is a simple example, but read the documentation or look at the site's source for more.
```
<div class="card">
  <div class="card-body">
    <h4 class="card-title">Card title</h4>
    <h6 class="card-subtitle mb-2 text-muted">Card subtitle</h6>
    <p class="card-text">Fancy, isn't it?</p>
    <a href="#" class="card-link">Card link</a>
  </div>
</div>
```

### Jumbotron

[Jumbotrons](https://getbootstrap.com/docs/4.0/components/jumbotron/) are useful for featuring an
image or tagline for your game. They can flow with the rest of your content or take up the full
width of the page - Evennia's base site uses the former.
```
<div class="jumbotron jumbotron-fluid">
  <div class="container">
    <h1 class="display-3">Full Width Jumbotron</h1>
    <p class="lead">Look at the source of the default Evennia page for a regular Jumbotron</p>
  </div>
</div>
```

### Forms

[Forms](https://getbootstrap.com/docs/4.0/components/forms/) are highly customizable with Bootstrap.
For a more in-depth look at how to use forms and their styles in your own Evennia site, please read
over [the web character gen tutorial.](../Howtos/Web-Character-Generation.md)

## Further reading

Bootstrap also provides a huge amount of utilities, as well as styling and content elements. To learn more about them, please [read the Bootstrap docs](https://getbootstrap.com/docs/4.0/getting- started/introduction/) or read one of our other web tutorials.