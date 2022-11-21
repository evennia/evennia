# Extending the REST API

> *This tutorial assumes you have a basic understanding of the `web` folder structure. If you don't, please read [the page on the website](https://www.evennia.com/docs/1.0-dev/Components/Website.html) and make sure you understand it before you come back!*

For this guide, we'll be adding an `inventory` action to the `characters` endpoint, showing all objects being _worn_ and _carried_ by a character.

> "worn versus carried" isn't built into core Evennia, but it's a common thing to add. This guide uses a `.db.worn` attribute to identify gear, but will explain how to reference your own mechanic too.

The first thing you should do is review the [REST API](https://www.evennia.com/docs/1.0-dev/Components/Web-API.html) documentation page. It's not very long, but it covers how to turn the API on and which parts of django you should be familiar with.

Once you've read that and successfully visited `/api/characters/`, it's time to get started!

## Creating your own viewset

The first thing you'll need to do is define your own views module. Create a blank file: `mygame/web/api/views.py`

> A *view* is the python code that tells django what data to put on a page, while a *template* tells django how to display that data. For more in-depth information, you can read the django documentation. ([docs for views](https://docs.djangoproject.com/en/4.1/topics/http/views/), [docs for templates](https://docs.djangoproject.com/en/4.1/topics/templates/))

The default REST API endpoints are controlled by classes in `evennia/web/api/views.py` - you could copy that entire file directly and use it, but we're going to focus on changing the minimum.

To start, we'll reimplement the default `characters` endpoint: a child view of the `objects` endpoint that can only access characters.

```python
"""
mygame/web/api/views.py

Customized views for the REST API
"""
# we'll need these from django's rest framework to make our view work
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

# this implements all the basic Evennia Object endpoint logic, so we're inheriting from it
from evennia.web.api.views import ObjectDBViewSet

# and we need this to filter our character view
from evennia.objects.objects import DefaultCharacter

# our own custom view
class CharacterViewSet(ObjectDBViewSet):
    """
    A customized Character view that adds an inventory detail
    """
    queryset = DefaultCharacter.objects.all_family()
```

## Setting up the urls

Now that we have a viewset of our own, we can create our own urls module and change the `characters` endpoint path to point to ours.

> Evennia's [Game website](https://www.evennia.com/docs/1.0-dev/Components/Website.html) page demonstrates how to use the `urls.py` module for the main website - if you haven't gone over that page yet, now is a good time.

The API routing is more complicated than the website or webclient routing, so you need to copy the entire module from evennia into your game instead of patching on changes. Copy the file from `evennia/web/api/urls.py` to your folder, `mygame/web/api/urls.py` and open it in your editor.

Import your new views module, then find and update the `characters` path to use your own viewset.

```python
# mygame/web/api/urls.py

from django.urls import path
from django.views.generic import TemplateView
from rest_framework.schemas import get_schema_view

from evennia.web.api.root import APIRootRouter
from evennia.web.api import views

from . import views as my_views # <--- NEW

app_name = "api"

router = APIRootRouter()
router.trailing_slash = "/?"
router.register(r"accounts", views.AccountDBViewSet, basename="account")
router.register(r"objects", views.ObjectDBViewSet, basename="object")
router.register(r"characters", my_views.CharacterViewSet, basename="character") # <--- MODIFIED
router.register(r"exits", views.ExitViewSet, basename="exit")
router.register(r"rooms", views.RoomViewSet, basename="room")
router.register(r"scripts", views.ScriptDBViewSet, basename="script")
router.register(r"helpentries", views.HelpViewSet, basename="helpentry")

urlpatterns = router.urls

urlpatterns += [
    # openapi schema
    path(
        "openapi",
        get_schema_view(title="Evennia API", description="Evennia OpenAPI Schema", version="1.0"),
        name="openapi",
    ),
    # redoc auto-doc (based on openapi schema)
    path(
        "redoc/",
        TemplateView.as_view(
            template_name="rest_framework/redoc.html", extra_context={"schema_url": "api:openapi"}
        ),
        name="redoc",
    ),
]
```

We've almost got it pointing at our new view now. The last step is to add your own API urls - `web.api.urls` - to your web root url module. Otherwise it will continue pointing to the default API router and we'll never see our changes.

Open `mygame/web/urls.py` in your editor and add a new path for "api/", pointing to `web.api.urls`. The final file should look something like this:

```python
# mygame/web/urls.py

from django.urls import path, include

# default evennia patterns
from evennia.web.urls import urlpatterns as evennia_default_urlpatterns

# add patterns
urlpatterns = [
    # website
    path("", include("web.website.urls")),
    # webclient
    path("webclient/", include("web.webclient.urls")),
    # web admin
    path("admin/", include("web.admin.urls")),
        
    # the new API path
    path("api/", include("web.api.urls")),
]

# 'urlpatterns' must be named such for django to find it.
urlpatterns = urlpatterns + evennia_default_urlpatterns
```

Restart your evennia game - `evennia reboot` from the command line for a full restart of the game AND portal - and try to get `/api/characters/` again. If it works exactly like before, you're ready to move on to the next step!

## Adding a new detail

Head back over to your character view class - it's time to start adding our inventory.

The usual "page" in a REST API is called an *endpoint* and is what you typically access. e.g. `/api/characters/` is the "characters" endpoint, and `/api/characters/:id` is the endpoint for individual characters.

> The `:` in an API path means that it's a variable - you don't directly access that exact path. Instead, you'd take your character ID (e.g. 1) and use that instead: `/api/characters/1`

However, an endpoint can also have one or more *detail* views, which function like a sub-point. We'll be adding *inventory* as a detail to our character endpoint, which will look like `/api/characters/:id/inventory`

With the django REST framework, adding a new detail is as simple as adding a decorated method to the view set class - the `@action` decorator. Since checking your inventory is just data retrieval, we'll only want to permit the `GET` method, and we're adding this action as an API detail, so our decorator will look like this:
```python
@action(detail=True, methods=["get"])
```

> There are situations where you might want a detail or endpoint that isn't just data retrieval: for example, *buy* or *sell* on an auction-house listing. In those cases, you would use *put* or *post* instead. For further reading on what you can do with `@action` and ViewSets, visit [the django REST framework documentation](https://www.django-rest-framework.org/api-guide/viewsets/)

When adding a function as a detail action, the name of our function will be the same as the detail. Since we want an `inventory` action we'll define an `inventory` function.

```python
"""
mygame/web/api/views.py

Customized views for the REST API
"""
# we'll need these from django's rest framework to make our view work
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

# this implements all the basic Evennia Object endpoint logic, so we're inheriting from it
from evennia.web.api.views import ObjectDBViewSet

# and we need this to filter our character view
from evennia.objects.objects import DefaultCharacter

# our own custom view
class CharacterViewSet(ObjectDBViewSet):
    """
    A customized Character view that adds an inventory detail
    """
    queryset = DefaultCharacter.objects.all_family()

    # !! NEW
    @action(detail=True, methods=["get"])
    def inventory(self, request, pk=None):
        return Response("your inventory", status=status.HTTP_200_OK )
```

Get your character's ID - it's the same as your dbref but without the # - and then `evennia reboot` again. Now you should be able to call your new characters action: `/api/characters/1/inventory` (assuming you're looking at character #1) and it'll return the string "your inventory"

## Creating a Serializer

A simple string isn't very useful, though. What we want is the character's actual inventory - and for that, we need to set up our own serializer.

Generally speaking, a *serializer* turns a set of data into a specially formatted string that can be sent in a data stream - usually JSON. Django REST serializers are special classes and functions which take python objects and convert them into API-ready formats. So, just like for the viewset, django and evennia have done a lot of the heavy lifting for us already.

> You can get a more in-depth look at django serializers on [the django REST framework serializer docs](https://www.django-rest-framework.org/api-guide/serializers/)

Instead of writing our own serializer, we'll inherit from evennia's pre-existing serializers and extend them for our own purpose. To do that, create a new file `mygame/web/api/serializers.py` and start by adding in the imports you'll need.

```python
# the base serializing library for the framework
from rest_framework import serializers

# the handy classes Evennia already prepared for us
from evennia.web.api.serializers import TypeclassSerializerMixin, SimpleObjectDBSerializer

# and the DefaultObject typeclass, for the necessary db model information
from evennia.objects.objects import DefaultObject
```

Next, we'll be defining our own serializer class. Since it's for retrieving inventory data, we'll name it appropriately.

```python
class InventorySerializer(TypeclassSerializerMixin, serializers.ModelSerializer):
    """
    Serializing an inventory
    """
    
    # these define the groups of items
    worn = serializers.SerializerMethodField()
    carried = serializers.SerializerMethodField()
    
    class Meta:
        model = DefaultObject
        fields = [
            "id", # required field
            # add these to match the properties you defined
            "worn",
            "carried",
        ]
        read_only_fields = ["id"]
```
The `Meta` class defines which fields will be used in the final serialized string. The `id` field is from the base ModelSerializer, but you'll notice that the two others - `worn` and `carried` - are defined as properties to `SerializerMethodField`. That tells the framework to look for matching method names in the form `get_X` when serializing.

Which is why our next step is to add those methods! We defined the properties `worn` and `carried`, so the methods we'll add are `get_worn` and `get_carried`. They'll be static methods - that is, they don't include `self` - since they don't need to reference the serializer class itself.

```python
    # these methods filter the character's contents based on the `worn` attribute
    def get_worn(character):
        """
        Serializes only worn objects in the target's inventory.
        """
        worn = [obj for obj in character.contents if obj.db.worn]
        return SimpleObjectDBSerializer(worn, many=True).data
    
    def get_carried(character):
        """
        Serializes only non-worn objects in the target's inventory.
        """
        carried = [obj for obj in character.contents if not obj.db.worn]
        return SimpleObjectDBSerializer(carried, many=True).data
```

For this guide, we're assuming that whether an object is being worn or not is stored in the `worn` db attribute and filtering based on that attribute. This can easily be done differently to match your own game's mechanics: filtering based on a tag, calling a custom method on your character that returns the right list, etc.

If you want to add in more details - grouping carried items by typing, or dividing up armor vs weapons, you'd just need to add or change the properties, fields, and methods.

> Remember: `worn = serializers.SerializerMethodField()` is how the API knows to use `get_worn`, and `Meta.fields` is the list of fields that will actually make it into the final JSON.

Your final file should look like this:

```python
# mygame/web/api/serializers.py

# the base serializing library for the framework
from rest_framework import serializers

# the handy classes Evennia already prepared for us
from evennia.web.api.serializers import TypeclassSerializerMixin, SimpleObjectDBSerializer

# and the DefaultObject typeclass, for the necessary db model information
from evennia.objects.objects import DefaultObject

class InventorySerializer(TypeclassSerializerMixin, serializers.ModelSerializer):
    """
    Serializing an inventory
    """
    
    # these define the groups of items
    worn = serializers.SerializerMethodField()
    carried = serializers.SerializerMethodField()
    
    class Meta:
        model = DefaultObject
        fields = [
            "id", # required field
            # add these to match the properties you defined
            "worn",
            "carried",
        ]
        read_only_fields = ["id"]

    # these methods filter the character's contents based on the `worn` attribute
    def get_worn(character):
        """
        Serializes only worn objects in the target's inventory.
        """
        worn = [obj for obj in character.contents if obj.db.worn]
        return SimpleObjectDBSerializer(worn, many=True).data
    
    def get_carried(character):
        """
        Serializes only non-worn objects in the target's inventory.
        """
        carried = [obj for obj in character.contents if not obj.db.worn]
        return SimpleObjectDBSerializer(carried, many=True).data
```

## Using your serializer

Now let's go back to our views file, `mygame/web/api/views.py`. Add our new serializer with the rest of the imports:

```python
from .serializers import InventorySerializer
```

Then, update our `inventory` detail to use our serializer.
```python
    @action(detail=True, methods=["get"])
    def inventory(self, request, pk=None):
        obj = self.get_object()
        return Response( InventorySerializer(obj).data, status=status.HTTP_200_OK )
```

Your views file should now look like this:

```python
"""
mygame/web/api/views.py

Customized views for the REST API
"""
# we'll need these from django's rest framework to make our view work
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

# this implements all the basic Evennia Object endpoint logic, so we're inheriting from it
from evennia.web.api.views import ObjectDBViewSet

# and we need this to filter our character view
from evennia.objects.objects import DefaultCharacter

from .serializers import InventorySerializer # <--- NEW

# our own custom view
class CharacterViewSet(ObjectDBViewSet):
    """
    A customized Character view that adds an inventory detail
    """
    queryset = DefaultCharacter.objects.all_family()

    @action(detail=True, methods=["get"])
    def inventory(self, request, pk=None):
        return Response( InventorySerializer(obj).data, status=status.HTTP_200_OK ) # <--- MODIFIED
```

That'll use our new serializer to get our character's inventory. Except... not quite.

Go ahead and try it: `evennia reboot` and then `/api/characters/1/inventory` like before. Instead of returning the string "your inventory", you should get an error saying you don't have permission. Don't worry - that means it's successfully referencing the new serializer. We just haven't given it permission to access the objects yet.

## Customizing API permissions

Evennia comes with its own custom API permissions class, connecting the API permissions to the in-game permission hierarchy and locks system. Since we're trying to access the object's data now, we need to pass the `has_object_permission` check as well as the general permission check - and that default permission class hardcodes actions into the object permission checks.

Since we've added a new action - `inventory` - to our characters endpoint, we need to use our own custom permissions on our characters endpoint as well. Create one more module file: `mygame/web/api/permissions.py`

Like with the previous classes, we'll be inheriting from the original and extending it to take advantage of all the work Evennia already does for us.

```python
# mygame/web/api/permissions.py

from evennia.web.api.permissions import EvenniaPermission

class CharacterPermission(EvenniaPermission):
    
    def has_object_permission(self, request, view, obj):
        """
        Checks object-level permissions after has_permission
        """
        # our new permission check
        if view.action == "inventory":
            return self.check_locks(obj, request.user, self.view_locks)

        # if it's not an inventory action, run through all the default checks
        return super().has_object_permission(request, view, obj)
```

That's the whole permission class! For our final step, we need to use it in our characters view by importing it and setting the `permission_classes` property.

Once you've done that, your final `views.py` should look like this:

```python
"""
mygame/web/api/views.py

Customized views for the REST API
"""
# we'll need these from django's rest framework to make our view work
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

# this implements all the basic Evennia Object endpoint logic, so we're inheriting from it
from evennia.web.api.views import ObjectDBViewSet

# and we need this to filter our character view
from evennia.objects.objects import DefaultCharacter

from .serializers import InventorySerializer
from .permissions import CharacterPermission # <--- NEW

# our own custom view
class CharacterViewSet(ObjectDBViewSet):
    """
    A customized Character view that adds an inventory detail
    """
    permission_classes = [CharacterPermission] # <--- NEW
    queryset = DefaultCharacter.objects.all_family()

    @action(detail=True, methods=["get"])
    def inventory(self, request, pk=None):
        obj = self.get_object()
        return Response( InventorySerializer(obj).data, status=status.HTTP_200_OK )
```

One last `evennia reboot` - now you should be able to get `/api/characters/1/inventory` and see everything your character has, neatly divided into "worn" and "carried".

## Next Steps

That's it! You've learned how to customize your own REST endpoint for Evennia, add new endpoint details, and serialize data from your game's objects for the REST API. With those tools, you can take any in-game data you want and make it available - or even modifiable - with the API.

If you want a challenge, try taking what you learned and implementing a new `desc` detail that will let you `GET` the existing character desc _or_ `PUT` a new desc. (Tip: check out how evennia's REST permissions module works, and the `set_attribute` methods in the default evennia REST API views.)

> For a more in-depth look at the django REST framework, you can go through [their tutorial](https://www.django-rest-framework.org/tutorial/1-serialization/) or straight to [the django REST framework API docs](https://www.django-rest-framework.org/api-guide/requests/)