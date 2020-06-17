# Bootstrap Components and Utilities

Bootstrap provides many utilities and components you can use when customizing Evennia's web
presence. We'll go over a few examples here that you might find useful.
> Please take a look at either [the basic web tutorial](Add-a-simple-new-web-page) or [the web
character view tutorial](Web-Character-View-Tutorial)
> to get a feel for how to add pages to Evennia's website to test these examples.

## General Styling
Bootstrap provides base styles for your site. These can be customized through CSS, but the default
styles are intended to provide a consistent, clean look for sites.

### Color
Most elements can be styled with default colors. [Take a look at the
documentation](https://getbootstrap.com/docs/4.0/utilities/colors/) to learn more about these colors
- suffice to say, adding a class of text-* or bg-*, for instance, text-primary, sets the text color
or background color.

### Borders
Simply adding a class of 'border' to an element adds a border to the element. For more in-depth
info, please [read the documentation on
borders.](https://getbootstrap.com/docs/4.0/utilities/borders/).
```
<span class="border border-dark"></span>
```
You can also easily round corners just by adding a class.
```
<img src="..." class="rounded" />
```

### Spacing
Bootstrap provides classes to easily add responsive margin and padding. Most of the time, you might
like to add margins or padding through CSS itself - however these classes are used in the default
Evennia site. [Take a look at the docs](https://getbootstrap.com/docs/4.0/utilities/spacing/) to
learn more.

***
## Components

### Buttons
[Buttons](https://getbootstrap.com/docs/4.0/components/buttons/) in Bootstrap are very easy to use -
button styling can be added to `<button>`, `<a>`, and `<input>` elements.
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
over [the web character gen tutorial.](Web-Character-Generation)