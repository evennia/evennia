from django import template

register = template.Library()


@register.filter(name="addclass")
def addclass(field, given_class):
    existing_classes = field.field.widget.attrs.get("class", None)
    if existing_classes:
        if existing_classes.find(given_class) == -1:
            # if the given class doesn't exist in the existing classes
            classes = existing_classes + " " + given_class
        else:
            classes = existing_classes
    else:
        classes = given_class
    return field.as_widget(attrs={"class": classes})
