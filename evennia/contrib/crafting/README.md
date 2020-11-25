# Crafting system 

Contrib - Griatch 2020

This implements a full crafting system. The principle is that of a 'recipe':

  object1 + object2 + ... -> craft_recipe -> objectA, objectB, ...

The recipe is a class that specifies input and output hooks. By default the
input is a list of object-tags (using the "crafting_material" tag-category)
and objects passing this check must be passed into the recipe.

The output is given by a set of prototypes. If the input is correct and other
checks are passed (such as crafting skill, for example), these prototypes will
be used to generate the new objects being 'crafted'.

Each recipe is a stand-alone entity which allows for very advanced customization
for every recipe - for example one could have a recipe where the input ingredients
are not destroyed in the process, or which require other properties of the input
(such as a 'quality').
