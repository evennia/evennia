# 扩展 REST API

```{sidebar}
像 _worn_ 或 _carried_ 这样的概念并不是 Evennia 的核心内置功能，但这是一个常见的添加功能。本指南使用 `.db.worn` 属性来标识装备，但也会解释如何引用您自己的机制。
```
默认情况下，Evennia 的 [REST API](../Components/Web-API.md) 为标准实体提供端点。其中一个端点是 `/api/characters/`，返回角色的信息。在本教程中，我们将通过向 `/characters` 端点添加一个 `inventory` 操作来扩展它，显示角色所 _穿戴_ 和 _携带_ 的所有物品。

## 创建自己的视图集

```{sidebar} 视图和模板
*视图* 是告诉 Django 在页面上放置哪些数据的 Python 代码，而 *模板* 则告知 Django 如何显示这些数据。有关更深入的信息，您可以阅读 Django [视图文档](https://docs.djangoproject.com/en/4.1/topics/http/views/) 和 [模板文档](https://docs.djangoproject.com/en/4.1/topics/templates/)。
```
您需要做的第一件事是定义您自己的 `views.py` 模块。

创建一个空文件：`mygame/web/api/views.py`

默认的 REST API 端点由 `evennia/web/api/views.py` 中的类控制——您可以复制整个文件并使用它，但我们将专注于进行最小的更改。

首先，我们将重新实现处理来自 `characters/` 端点请求的默认 [CharacterViewSet](CharacterViewSet)。这是一个只能访问角色的 `objects` 端点的子类。

```python
# 在 mygame/web/api/views.py 中

# 我们需要从 Django 的 REST 框架中获取这些内容来使我们的视图工作
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

# 这实现了所有基本的 Evennia 对象端点逻辑，因此我们从中继承
from evennia.web.api.views import ObjectDBViewSet

# 我们还需要这个来过滤我们的角色视图
from evennia.objects.objects import DefaultCharacter

# 我们自己的自定义视图
class CharacterViewSet(ObjectDBViewSet):
    """
    自定义的角色视图，添加了库存细节
    """
    queryset = DefaultCharacter.objects.all_family()
```

## 设置 URL

现在我们有了自己的视图集，可以创建自己的 URL 模块，并将 `characters` 端点路径更改为指向我们自己的视图。

```{sidebar}
Evennia 的 [游戏网站](../Components/Website.md) 页面演示了如何使用 `urls.py` 模块为主网站提供服务——如果您还没有查看过该页面，现在是个好时机。
```
API 路由比网站或网页客户端路由更复杂，因此您需要将整个模块从 Evennia 复制到您的游戏中，而不是进行补丁性的更改。将文件从 `evennia/web/api/urls.py` 复制到您的文件夹 `mygame/web/api/urls.py` 并在编辑器中打开它。

导入您的新视图模块，然后找到并更新 `characters` 路径以使用您自己的视图集。

```python
# mygame/web/api/urls.py

from django.urls import path
from django.views.generic import TemplateView
from rest_framework.schemas import get_schema_view

from evennia.web.api.root import APIRootRouter
from evennia.web.api import views

from . import views as my_views # <--- 新增

app_name = "api"

router = APIRootRouter()
router.trailing_slash = "/?"
router.register(r"accounts", views.AccountDBViewSet, basename="account")
router.register(r"objects", views.ObjectDBViewSet, basename="object")
router.register(r"characters", my_views.CharacterViewSet, basename="character") # <--- 修改
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
    # redoc 自动文档（基于 openapi schema）
    path(
        "redoc/",
        TemplateView.as_view(
            template_name="rest_framework/redoc.html", extra_context={"schema_url": "api:openapi"}
        ),
        name="redoc",
    ),
]
```

我们几乎已经将它指向新的视图。最后一步是将你的 API URL - `web.api.urls` - 添加到你的网站根 URL 模块。否则它将继续指向默认的 API 路由器，我们永远不会看到我们的更改。

在编辑器中打开 `mygame/web/urls.py`，并为 "api/" 添加一个新路径，指向 `web.api.urls`。最终文件应如下所示：

```python
# mygame/web/urls.py

from django.urls import path, include

# 默认的 Evennia 模式
from evennia.web.urls import urlpatterns as evennia_default_urlpatterns

# 添加模式
urlpatterns = [
    # 网站
    path("", include("web.website.urls")),
    # 网页客户端
    path("webclient/", include("web.webclient.urls")),
    # 网站管理
    path("admin/", include("web.admin.urls")),
        
    # 新的 API 路径
    path("api/", include("web.api.urls")),
]

# 'urlpatterns' 必须命名，以便 Django 能找到它。
urlpatterns = urlpatterns + evennia_default_urlpatterns
```

重启您的 Evennia 游戏 - 从命令行使用 `evennia reboot` 完全重启游戏和门户 - 然后再次尝试访问 `/api/characters/`。如果它的工作方式与之前完全相同，那么您就可以继续进行下一步了！

## 添加新细节

回到您的角色视图类——现在是时候开始添加库存了。

REST API 中的常规“页面”称为 *端点*，这是您通常访问的内容。例如，`/api/characters/` 是“角色”端点，而 `/api/characters/:id` 是单个角色的端点。

```{sidebar} 那个冒号是什么？
API 路径中的 `:` 表示这是一个 *变量* - 您不能直接访问那个确切的路径。相反，您可以使用您的角色 ID（例如 1）代替：`/api/characters/1`
```

然而，端点也可以有一个或多个 *详细* 视图，其功能类似于子端点。我们将添加 *inventory* 作为角色端点的详细信息，形式为 `/api/characters/:id/inventory`。

使用 Django REST 框架，添加新细节的方法很简单，就是在视图集类中添加一个装饰的方法 - `@action` 装饰器。由于检查库存只是数据检索，我们只想允许 `GET` 方法，并且我们将此操作作为 API 细节，因此我们的装饰器看起来如下：
```python
@action(detail=True, methods=["get"])
```

> 有些情况下，您可能希望某个细节或端点不只是数据检索：例如，拍卖行列表中的 *buy* 或 *sell*。在这些情况下，您将使用 *put* 或 *post*。有关使用 `@action` 和视图集可以做的事情的更多阅读，请访问 [Django REST 框架文档](https://www.django-rest-framework.org/api-guide/viewsets/)。

当将函数作为详细操作添加时，函数的名称将与操作的名称相同。由于我们希望有一个 `inventory` 操作，因此我们将定义一个 `inventory` 函数。

```python
"""
mygame/web/api/views.py

用于 REST API 的自定义视图
"""
# 我们需要从 Django 的 REST 框架中获取这些内容来使我们的视图工作
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

# 这实现了所有基本的 Evennia 对象端点逻辑，因此我们从中继承
from evennia.web.api.views import ObjectDBViewSet

# 和我们需要这个来过滤我们的角色视图
from evennia.objects.objects import DefaultCharacter

# 我们自己的自定义视图
class CharacterViewSet(ObjectDBViewSet):
    """
    自定义的角色视图，添加了库存细节
    """
    queryset = DefaultCharacter.objects.all_family()

    # !! 新增
    @action(detail=True, methods=["get"])
    def inventory(self, request, pk=None):
        return Response("您的库存", status=status.HTTP_200_OK)
```

获取角色的 ID - 它与您的 dbref 一样，但没有 # - 然后再次执行 `evennia reboot`。现在您应该能够调用您的新角色操作：`/api/characters/1/inventory`（假设您正在查看角色 #1），它将返回字符串 "您的库存"。

## 创建序列化器

然而，仅仅返回一个简单的字符串并没有多大用处。我们想要的是角色的实际库存——为此，我们需要设置自己的 *序列化器*。

```{sidebar} Django 序列化器
您可以在 [Django REST 框架序列化器文档](https://www.django-rest-framework.org/api-guide/serializers/) 中获取有关 Django 序列化器的更深入了解。
```
一般来说，*序列化器* 会将一组数据转换为特殊格式的字符串，以便在数据流中发送 - 通常是 JSON。Django REST 序列化器是特别的类和函数，可以将 Python 对象转换为 API 准备就绪的格式。因此，就像视图集一样，Django 和 Evennia 已经为我们完成了很多繁重的工作。

我们将继承 Evennia 的现有序列化器并扩展它以满足我们的需求，而不是自己编写序列化器。为此，创建一个新文件 `mygame/web/api/serializers.py` 并开始添加您所需的导入。

```python
# 框架的基本序列化库
from rest_framework import serializers

# Evennia 为我们准备的便利类
from evennia.web.api.serializers import TypeclassSerializerMixin, SimpleObjectDBSerializer

# 和必要的数据库模型信息的 DefaultObject 类型类
from evennia.objects.objects import DefaultObject
```

接下来，我们将定义自己的序列化器类。由于它用于检索库存数据，因此我们将其命名为适当。

```python
class InventorySerializer(TypeclassSerializerMixin, serializers.ModelSerializer):
    """
    序列化库存
    """
    
    # 这些定义了物品的组
    worn = serializers.SerializerMethodField()
    carried = serializers.SerializerMethodField()
    
    class Meta:
        model = DefaultObject
        fields = [
            "id", # 必需字段
            # 添加这些以匹配您定义的属性
            "worn",
            "carried",
        ]
        read_only_fields = ["id"]
```
`Meta` 类定义了将在最终序列化字符串中使用的字段。`id` 字段来自基础 ModelSerializer，但您会注意到另外两个字段 - `worn` 和 `carried` - 被定义为 `SerializerMethodField` 的属性。这告诉框架在序列化时查找形如 `get_X` 的匹配方法名称。

这就是我们下一步要添加这些方法的原因！我们定义了属性 `worn` 和 `carried`，因此我们将添加 `get_worn` 和 `get_carried` 方法。它们将是静态方法——即不包含 `self`——因为它们不需要引用序列化器类本身。

```python
    # 这些方法根据 `worn` 属性过滤角色的内容
    def get_worn(character):
        """
        仅序列化目标库存中穿戴的物品。
        """
        worn = [obj for obj in character.contents if obj.db.worn]
        return SimpleObjectDBSerializer(worn, many=True).data
    
    def get_carried(character):
        """
        仅序列化目标库存中未穿戴的物品。
        """
        carried = [obj for obj in character.contents if not obj.db.worn]
        return SimpleObjectDBSerializer(carried, many=True).data
```

在本指南中，我们假设物品是否被穿戴存储在 `worn` 数据库属性中，并基于该属性进行过滤。根据您的游戏机制，这可以轻松地以不同的方式进行匹配：根据标签进行过滤，调用角色的自定义方法以返回正确的列表等。

如果您想添加更多详细信息 - 按类型对携带的物品进行分组，或将盔甲与武器区分开，您只需添加或更改属性、字段和方法。

> 请记住：`worn = serializers.SerializerMethodField()` 是 API 知道使用 `get_worn` 的方法，而 `Meta.fields` 则是最终将“输入” JSON 的字段列表。

您的最终文件应如下所示：

```python
# mygame/web/api/serializers.py

# 框架的基本序列化库
from rest_framework import serializers

# Evennia 为我们准备的便利类
from evennia.web.api.serializers import TypeclassSerializerMixin, SimpleObjectDBSerializer

# 和必要的数据库模型信息的 DefaultObject 类型类
from evennia.objects.objects import DefaultObject

class InventorySerializer(TypeclassSerializerMixin, serializers.ModelSerializer):
    """
    序列化库存
    """
    
    # 这些定义了物品的组
    worn = serializers.SerializerMethodField()
    carried = serializers.SerializerMethodField()
    
    class Meta:
        model = DefaultObject
        fields = [
            "id", # 必需字段
            # 添加这些以匹配您定义的属性
            "worn",
            "carried",
        ]
        read_only_fields = ["id"]

    # 这些方法根据 `worn` 属性过滤角色的内容
    def get_worn(character):
        """
        仅序列化目标库存中穿戴的物品。
        """
        worn = [obj for obj in character.contents if obj.db.worn]
        return SimpleObjectDBSerializer(worn, many=True).data
    
    def get_carried(character):
        """
        仅序列化目标库存中未穿戴的物品。
        """
        carried = [obj for obj in character.contents if not obj.db.worn]
        return SimpleObjectDBSerializer(carried, many=True).data
```

## 使用序列化器

现在让我们回到视图文件 `mygame/web/api/views.py`。将我们的新序列化器与其他导入一起添加：

```python
from .serializers import InventorySerializer
```

然后，更新我们的 `inventory` 详细信息以使用我们的序列化器。
```python
    @action(detail=True, methods=["get"])
    def inventory(self, request, pk=None):
        obj = self.get_object()
        return Response( InventorySerializer(obj).data, status=status.HTTP_200_OK )
```

现在您的视图文件应如下所示：

```python
"""
mygame/web/api/views.py

用于 REST API 的自定义视图
"""
# 我们需要从 Django 的 REST 框架中获取这些内容来使我们的视图工作
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

# 这实现了所有基本的 Evennia 对象端点逻辑，因此我们从中继承
from evennia.web.api.views import ObjectDBViewSet

# 和我们需要这个来过滤我们的角色视图
from evennia.objects.objects import DefaultCharacter

from .serializers import InventorySerializer # <--- 新增

# 我们自己的自定义视图
class CharacterViewSet(ObjectDBViewSet):
    """
    自定义的角色视图，添加了库存细节
    """
    queryset = DefaultCharacter.objects.all_family()

    @action(detail=True, methods=["get"])
    def inventory(self, request, pk=None):
        return Response( InventorySerializer(obj).data, status=status.HTTP_200_OK ) # <--- 修改
```

这将使用我们的新序列化器来获取角色的库存。不过……并不完全。

继续尝试：`evennia reboot`，然后像之前一样访问 `/api/characters/1/inventory`。此时，您应该得到一个错误，提示您没有权限。别担心——这意味着它成功引用了新的序列化器。我们只需没有赋予它访问对象的权限。

## 自定义 API 权限

Evennia 带有其自己的自定义 API 权限类，将 API 权限与游戏内权限级别和锁定系统连接起来。由于我们现在试图访问对象的数据，因此我们需要通过 `has_object_permission` 检查以及一般权限检查——而默认的权限类在对象权限检查中硬编码了动作。

由于我们向角色端点添加了一个新操作 - `inventory`，我们还需要在角色端点上使用我们自己的自定义权限。再创建一个模块文件：`mygame/web/api/permissions.py`

与之前的类一样，我们将从原始类继承并扩展其功能，以利用 Evennia 已经为我们做的所有工作。

```python
# mygame/web/api/permissions.py

from evennia.web.api.permissions import EvenniaPermission

class CharacterPermission(EvenniaPermission):
    
    def has_object_permission(self, request, view, obj):
        """
        在 has_permission 之后检查对象级别的权限
        """
        # 我们的新权限检查
        if view.action == "inventory":
            return self.check_locks(obj, request.user, self.view_locks)

        # 如果不是一个库存操作，则通过所有默认检查
        return super().has_object_permission(request, view, obj)
```

这就是整个权限类！在最后一步中，我们需要通过导入它并设置 `permission_classes` 属性来在角色视图中使用它。

完成后，您的最终 `views.py` 应如下所示：

```python
"""
mygame/web/api/views.py

用于 REST API 的自定义视图
"""
# 我们需要从 Django 的 REST 框架中获取这些内容来使我们的视图工作
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

# 这实现了所有基本的 Evennia 对象端点逻辑，因此我们从中继承
from evennia.web.api.views import ObjectDBViewSet

# 和我们需要这个来过滤我们的角色视图
from evennia.objects.objects import DefaultCharacter

from .serializers import InventorySerializer
from .permissions import CharacterPermission # <--- 新增

# 我们自己的自定义视图
class CharacterViewSet(ObjectDBViewSet):
    """
    自定义的角色视图，添加了库存细节
    """
    permission_classes = [CharacterPermission] # <--- 新增
    queryset = DefaultCharacter.objects.all_family()

    @action(detail=True, methods=["get"])
    def inventory(self, request, pk=None):
        obj = self.get_object()
        return Response( InventorySerializer(obj).data, status=status.HTTP_200_OK )
```

最后一次 `evennia reboot` - 现在您应该能够访问 `/api/characters/1/inventory`，查看您角色的所有物品，整齐划分为“穿戴”和“携带”。

## 下一步

```{sidebar} Django REST 框架
要更深入了解 Django REST 框架，您可以查看 [它们的教程](https://www.django-rest-framework.org/tutorial/1-serialization/) 或直接查看 [Django REST 框架 API 文档](https://www.django-rest-framework.org/api-guide/requests/)。
```
就是这样！您已经学习了如何自定义自己的 Evennia REST 端点，添加新的端点细节，以及从游戏对象序列化数据以供 REST API 使用。通过这些工具，您可以获取任何想要的游戏内数据，使其可用 - 甚至可修改 - 通过 API。

如果您想要一个挑战，尝试将您所学的内容应用于实现一个新的 `desc` 细节，以便您可以 `GET` 获取现有角色描述 _或_ `PUT` 新描述。（提示：查看 Evennia 的 REST 权限模块的工作原理，以及默认 Evennia REST API 视图中的 `set_attribute` 方法。）
