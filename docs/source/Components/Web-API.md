# Evennia REST API

Evennia makes its database accessible via a REST API found on
[http://localhost:4001/api](http://localhost:4001/api) if running locally with
default setup. The API allows you to retrieve, edit and create resources from
outside the game, for example with your own custom client or game editor.

While you can view and learn about the api in the web browser, it is really
meant to be accessed in code, by other programs.

The API is using [Django Rest Framework][drf]. This automates the process
of setting up _views_ (Python code) to process the result of web requests.
The process of retrieving data is similar to that explained on the
[Webserver](./Webserver) page, except the views will here return [JSON][json]
data for the resource you want. You can also _send_ such JSON data
in order to update the database from the outside.


## Usage

To activate the API, add this to your settings file.

    REST_API_ENABLED = True

The main controlling setting is `REST_FRAMEWORK`, which is a dict. The keys
`DEFAULT_LIST_PERMISSION` and `DEFAULT_CREATE_PERMISSIONS` control who may
view and create new objects via the api respectively. By default, users with
['Builder'-level permission](./Permissions) or higher may access both actions.

While the api is meant to be expanded upon, Evennia supplies several operations
out of the box. If you click the `Autodoc` button in the upper right of the `/api`
website you'll get a fancy graphical presentation of the available endpoints.

Here is an example of calling the api in Python using the standard `requests` library.

    >>> import requests
    >>> response = requests.get("https://www.mygame.com/api", auth=("MyUsername", "password123"))
    >>> response.json()
    {'accounts': 'http://www.mygame.com/api/accounts/',
     'objects': 'http://www.mygame.com/api/objects/',
    'characters': 'http://www.mygame.comg/api/characters/',
    'exits': 'http://www.mygame.com/api/exits/',
    'rooms': 'http://www.mygame.com/api/rooms/',
    'scripts': 'http://www.mygame.com/api/scripts/'
    'helpentries': 'http://www.mygame.com/api/helpentries/' }

To list a specific type of object:

    >>> response = requests.get("https://www.mygame.com/api/objects",
                                auth=("Myusername", "password123"))
    >>> response.json()
    {
    "count": 125,
    "next": "https://www.mygame.com/api/objects/?limit=25&offset=25",
    "previous": null,
    "results" : [{"db_key": "A rusty longsword", "id": 57, "db_location": 213, ...}]}

In the above example, it now displays the objects inside the "results" array,
while it has a "count" value for the number of total objects, and "next" and
"previous" links for the next and previous page, if any.  This is called
[pagination][pagination], and the link displays "limit" and "offset" as query
parameters that can be added to the url to control the output.


Other query parameters can be defined as [filters][filters] which allow you to
further narrow the results. For example, to only get accounts with developer
permissions:

    >>> response = requests.get("https://www.mygame.com/api/accounts/?permission=developer",
                                auth=("MyUserName", "password123"))
    >>> response.json()
    {
    "count": 1,
    "results": [{"username": "bob",...}]
    }

Now suppose that you want to use the API to create an [Object](./Objects):

    >>> data = {"db_key": "A shiny sword"}
    >>> response = requests.post("https://www.mygame.com/api/objects",
                                 data=data, auth=("Anotherusername", "mypassword"))
    >>> response.json()
    {"db_key": "A shiny sword", "id": 214, "db_location": None, ...}


Here we made a HTTP POST request to the `/api/objects` endpoint with the `db_key`
we wanted. We got back info for the newly created object. You can now make
another request with PUT (replace everything) or PATCH (replace only what you
provide). By providing the id to the endpoint (`/api/objects/214`),
we make sure to update the right sword:

    >>> data = {"db_key": "An even SHINIER sword", "db_location": 50}
    >>> response = requests.put("https://www.mygame.com/api/objects/214",
                                data=data, auth=("Anotherusername", "mypassword"))
    >>> response.json()
    {"db_key": "An even SHINIER sword", "id": 214, "db_location": 50, ...}


In most cases, you won't be making API requests to the backend with Python,
but with Javascript from some frontend application.
There are many Javascript libraries which are meant to make this process
easier for requests from the frontend, such as [AXIOS][axios], or using
the native [Fetch][fetch].

## Customizing the API

Overall, reading up on [Django Rest Framework ViewSets](https://www.django-rest-framework.org/api-guide/viewsets) and
other parts of their documentation is required for expanding and
customizing the API.

Check out the [Website](Website) page for help on how to override code, templates
and static files.
- API templates (for the web-display) is located in `evennia/web/api/templates/rest_framework/` (it must
  be named such to allow override of the original REST framework templates).
- Static files is in `evennia/web/api/static/rest_framework/`
- The api code is located in `evennia/web/api/` - the `url.py` file here is responsible for
  collecting all view-classes.

Contrary to other web components, there is no pre-made urls.py set up for
`mygame/web/api/`. This is because the registration of models with the api is
strongly integrated with the REST api functionality. Easiest is probably to
copy over `evennia/web/api/urls.py` and modify it in place.


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
