# Evennia API

## Synopsis

An API, or [Application Programming Interface][wiki-api], is a way of establishing rules
through which external services can use your program. In web development, it's
often that case that the 'frontend' of a web app is written in HTML and Javascript
and communicates with the 'backend' server through an API so that it can retrieve
information to populate web pages or process actions when users click buttons on
a web page.

The API contained within the web/api/ package is an implementation of the
[Django Rest Framework][drf]. It provides tools to allow you to quickly process
requests for resources and generate responses. URLs, called endpoints, are
mapped to python classes called views, which handle requests for resources.
Requests might contain data that is formatted as [JSON strings][json], which DRF
can convert into python objects for you, a process called deserialization.
When returning a response, it can also convert python objects into JSON
strings to send back to a client, which is called serialization. Because it's
such a common task to want to handle [CRUD][crud] operations for the django models that you use to represent database
objects (such as your Character typeclass, Room typeclass, etc), DRF makes 
this process very easy by letting you define [Serializers][serializers]
that largely automate the process of serializing your in-game objects into
JSON representations for sending them to a client, or for turning a JSON string
into a model for updating or creating it.

## Motivations For Using An API

Having an API can allow you to have richer interactions with client applications. For
example, suppose you want to allow players to send and receive in-game messages from
outside the game. You might define an endpoint that will retrieve all of a character's
messages and returns it as a JSON response. Then in a webpage, you have a button that
the user can click to make an [AJAX][ajax] request to that endpoint, retrieves the data, and
displays it on the page. You also provide a form to let them send messages, where the
submit button uses AJAX to make a POST request to that endpoint, sending along the
JSON data from the form, and then returns the response of the results. This works,
but then a tech-savvy player might ask if they can have their own application that
will retrieve messages periodically for their own computer. By having a [REST][rest] API that
they can use, they can create client applications of their own to retrieve or change
data.

Other examples of what you might use a RESTful API for would be players managing
tasks out-of-game like crafting, guild management, retrieving stats on their
characters, building rooms/grids, editing character details, etc. Any task that
doesn't require real-time 2-way interaction is a good candidate for an API endpoint.

## Sample requests

The API contains a number of views already defined. If the API is enabled, by
setting `REST_API_ENABLED = True` in your `settings.py`, endpoints will be
accessible by users who make authenticated requests as users with builder
permissions. Individual objects will check lockstrings to determine if the
user has permission to perform retrieve/update/delete actions upon them.
To start with, you can view a synopsis of endpoints by making a GET request
to the `yourgame/api/` endpoint by using the excellent [requests library][requests]:

```pythonstub
>>> import requests
>>> r = requests.get("https://www.mygame.com/api", auth=("user", "pw"))
>>> r.json()
{'accounts': 'http://www.mygame.com/api/accounts/',
 'objects': 'http://www.mygame.com/api/objects/',
'characters': 'http://www.mygame.comg/api/characters/',
'exits': 'http://www.mygame.com/api/exits/',
'rooms': 'http://www.mygame.com/api/rooms/',
'scripts': 'http://www.mygame.com/api/scripts/'}
```

To view an object, you might make a request like this:

```pythonstub
>>> import requests
>>> response = requests.get("https://www.mygame.com/api/objects/57",
                            auth=("Myusername", "password123"))
>>> response.json()
{"db_key": "A rusty longsword", "id": 57, "db_location": 213, ...}
```
The above example makes a GET request to the /objects/ endpoint to retrieve the
object with an ID of 57, retrieving basic data for it.

For listing a number of objects, you might do this:

```pythonstub
>>> response = requests.get("https://www.mygame.com/api/objects",
                            auth=("Myusername", "password123"))
>>> response.json()
{
"count": 125,
"next": "https://www.mygame.com/api/objects/?limit=25&offset=25",
"previous": null,
"results" : [{"db_key": "A rusty longsword", "id": 57, "db_location": 213, ...}]}
```

In the above example, it now displays the objects inside the "results" array,
while it has a "count" value for the number of total objects, and "next" and
"previous" links for the next and previous page, if any.  This is called
[pagination][pagination], and the link displays "limit" and "offset" as query
parameters that can be added to the url to control the output. Other query
parameters can be defined as [filters][filters] which allow you to further
narrow the results. For example, to only get accounts with developer
permissions:

```pythonstub
>>> response = requests.get("https://www.mygame.com/api/accounts/?permission=developer",
                            auth=("user", "pw"))
>>> response.json()
{
"count": 1,
"results": [{"username": "bob",...}]
}
```

Now suppose that you want
to use the API to create an object:

```pythonstub
>>> data = {"db_key": "A shiny sword"}
>>> response = requests.post("https://www.mygame.com/api/objects",
                             data=data, auth=("Anotherusername", "sekritpassword"))
>>> response.json()
{"db_key": "A shiny sword", "id": 214, "db_location": None, ...}
```

In the above example, you make a POST request to the /objects/ endpoint with
the name of the object you wish to create passed along as data. Now suppose you
decided you didn't like the name, and wanted to change it for the newly created
object:

```pythonstub
>>> data = {"db_key": "An even SHINIER sword", "db_location": 50}
>>> response = requests.put("https://www.mygame.com/api/objects/214",
                             data=data, auth=("Alsoauser", "Badpassword"))
>>> response.json()
{"db_key": "An even SHINIER sword", "id": 214, "db_location": 50, ...}             

``` 
By making a PUT request to the endpoint that includes the object ID, it becomes
a request to update the object with the specified data you pass along.

In most cases, you won't be making API requests to the backend with python,
but with Javascript from your frontend application.
There are many Javascript libraries which are meant to make this process 
easier for requests from the frontend, such as [AXIOS][axios], or using 
the native [Fetch][fetch].

[wiki-api]: https://en.wikipedia.org/wiki/Application_programming_interface
[drf]: https://www.django-rest-framework.org/
[pagination]: https://www.django-rest-framework.org/api-guide/pagination/
[filters]: https://www.django-rest-framework.org/api-guide/filtering/#filtering
[json]: https://en.wikipedia.org/wiki/JSON
[crud]: https://en.wikipedia.org/wiki/Create,_read,_update_and_delete
[serializers]: https://www.django-rest-framework.org/api-guide/serializers/
[ajax]: https://en.wikipedia.org/wiki/Ajax_(programming)
[rest]: https://en.wikipedia.org/wiki/Representational_state_transfer
[requests]: https://requests.readthedocs.io/en/master/
[axios]: https://github.com/axios/axios
[fetch]: https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API
