# Extending the REST API

*Note: This tutorial assumes you have a basic understanding of the `web` folder structure. If you don't, please read [the page on the website](https://www.evennia.com/docs/1.0-dev/Components/Website.html) and make sure you understand it before you come back!*

For this tutorial, we'll be adding an `inventory` action to the `characters` endpoint, showing all objects being _worn_ and _carried_ by a character. The first thing you should do is review the [REST API](https://www.evennia.com/docs/1.0-dev/Components/Web-API.html) documentation page. It's not very long, but it covers how to turn the API on and which parts of Django you should be familiar with.

Once you've read that and visited `/api/characters/`, it's time to get started!

## Creating your own viewset

The first thing you'll need to do is create your own views module: `<mygame>/web/api/views.py`

The default REST API endpoints are controlled by classes in `evennia/web/api/views.py` - you could copy that entire file directly and use it, but we're going to focus on changing the minimum.

To start, we'll reimplement the existing `characters` endpoint: a child view of the `objects` endpoint that can only access characters.

```python
"""
<mygame>/web/api/views.py

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

Now that we have a viewset of our own, we can create our own urls module and change the `characters` endpoint path to point to ours. The API routing is more complicated than the other `urls.py` files, so you need to copy evennia's from `evennia/web/api/urls.py` to your folder, `<mygame>/web/api/urls.py` and open it in your editor.

Import your new views module:

```python
from . import views as my_views
```

Then, find the `characters` path. The original line should look like this:

```python
router.register(r"characters", views.CharacterViewSet, basename="character")
```

You'll want to change that `views` to `my_views` to use your new viewset.

```python
router.register(r"characters", my_views.CharacterViewSet, basename="character")
```

**TODO: should this have a copy/paste of the final edited file?**

We've almost got it pointing at our new view now. The last step is to add your own API urls - `web.api.urls` - to your web root url module.

Open `web/urls.py` in your editor and add a new path for "api/", pointing to `web.api.urls`. The final file should look something like this:

```python
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

# 'urlpatterns' must be named such for Django to find it.
urlpatterns = urlpatterns + evennia_default_urlpatterns
```

Restart your evennia game - `evennia reboot` from the command line for a full restart of the game AND portal - and try to get `/api/characters/` again. If it works exactly like before, you're ready to move on to the next step!

## Adding a new detail

Head back over to your character view class - it's time to add our inventory action!

With the django rest framework, adding a new action is as simple as adding a decorated method to the view set class - the `@action` decorator. Since checking your inventory is just data retrieval, we'll only want to permit the `GET` method. Our decorator will look like this:
```python
@action(detail=True, methods=["get"])
```

The name of our function will be the same as in our API, so since we want an `inventory` action we'll name it `inventory`.

```python
@action(detail=True, methods=["get"])
def inventory(self, request, pk=None):
	return Response("your inventory", status=status.HTTP_200_OK )
```

Get your character's ID - it's the same as your dbref but without the # - and then `evennia reboot` again. Now you should be able to call your new characters action: `/api/characters/1/inventory` (assuming you're looking at character #1) and it'll return the string "your inventory"

## Creating a Serializer

A simple string isn't very useful, though. What we want is the character's actual inventory - and for that, we need to set up our own serializer.

Just like for the viewset, django and evennia have done a lot of the heavy lifting for us already: we can inherit from evennia's pre-existing serializers and extend them for our own purpose. To do that, create a new file, `<mygame>/web/api/serializers.py` and add in the imports you'll need.

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
	
	worn = serializers.SerializerMethodField()
	carried = serializers.SerializerMethodField()
	
	class Meta:
		model = DefaultObject
		fields = [
			"id",
			"worn",
			"carried",
		]
		read_only_fields = ["id"]
```
The `Meta` class defines which fields will be used in the final serialized string. The `id` field is from the base ModelSerializer, but you'll notice that the two others - `worn` and `carried` - are defined as properties to `SerializerMethodField`. That tells the framework to look for matching method names in the form `get_X` when serializing.

Which is why our next step is to add them! We'll be making them static methods since they don't need to reference the serializer class instance.

```python
	def get_worn(obj):
		"""
		Serializes only worn objects in the target's inventory.
		"""
		worn = [ob for ob in obj.contents if ob.db.worn]
		return SimpleObjectDBSerializer(worn, many=True).data
	
	def get_carried(obj):
		"""
		Serializes only non-worn objects in the target's inventory.
		"""
		carried = [ob for ob in obj.contents if not obj.db.worn]
		return SimpleObjectDBSerializer(carried, many=True).data
```

For this, we're assuming that whether an object is being worn or not is stored in the `worn` db attribute, but this can easily be done differently to match how your game's data is structured: `obj.tags.has('equipped')` for example. And you can easily divide up the returned data into different inventory sections by changing or adding the properties, fields, and methods attached.

Just remember: `worn = serializers.SerializerMethodField()` is how the API knows to use `get_worn`, and `Meta.fields` is the list of fields that will actually make it into the final JSON.

## Using your serializer

Now let's go back to our `views.py` - at this point, it should look something like this:

```python
"""
<mygame>/web/api/views.py

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

	@action(detail=True, methods=["get"])
	def inventory(self, request, pk=None):
		return Response("your inventory", status=status.HTTP_200_OK )
```

We want to import our new serializer up with the rest of the imports:
```python
from .serializers import InventorySerializer
```

And then, use it in our view:
```python
	@action(detail=True, methods=["get"])
	def inventory(self, request, pk=None):
		obj = self.get_object()
		return Response( InventorySerializer(obj).data, status=status.HTTP_200_OK )
```

That'll use our new serializer to get our character's inventory! Except... not quite. Go ahead and try it: `evennia reboot` and then `/api/characters/1/inventory` like before. Unlike before, you should get an error saying you don't have permission.

## Customizing API permissions

Evennia comes with its own custom API permissions class, connecting the API permissions to the in-game permission hierarchy and locks system. Since we're trying to access the object's data now, we need to pass the `has_object_permission` check as well as the general permission check - and that permission class hardcodes the actions into the object permission checks.

So, since we've added a new action - `inventory` - to our characters endpoint, we need to use our own custom permissions on our characters endpoint. Create one more module file: `<mygame>/web/api/permissions.py`

Like with the previous classes, we'll be inheriting from the original and extending it to take advantage of all the work Evennia already does for us.

```python
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

That's the whole permission class! For our final step, we just need to use it in our characters view by importing it and setting the `permission_classes` property.

Once you've done that, your final `views.py` should look like this:

```python
"""
<mygame>/web/api/views.py

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
from .permissions import CharacterPermission

# our own custom view
class CharacterViewSet(ObjectDBViewSet):
	"""
	A customized Character view that adds an inventory detail
	"""
	permission_classes = [CharacterPermission]
	queryset = DefaultCharacter.objects.all_family()

	@action(detail=True, methods=["get"])
	def inventory(self, request, pk=None):
		obj = self.get_object()
		return Response( InventorySerializer(obj).data, status=status.HTTP_200_OK )
```

One last `evennia reboot` - now you should be able to get `/api/characters/1/inventory` and see everything your character has, neatly divided into worn and carried.

And that's it!
