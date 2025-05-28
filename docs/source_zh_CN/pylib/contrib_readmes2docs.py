"""
Convert contribs' README files to proper documentation pages along with
an index.

"""
from collections import defaultdict
from glob import glob
from pathlib import Path
from os.path import abspath, dirname
from os.path import join as pathjoin
from os.path import sep

_EVENNIA_PATH = pathjoin(dirname(dirname(dirname(dirname(abspath(__file__))))))
_DOCS_PATH = pathjoin(_EVENNIA_PATH, "docs")

_SOURCE_DIR = pathjoin(_EVENNIA_PATH, "evennia", "contrib")
_OUT_DIR = pathjoin(_DOCS_PATH, "source_zh_CN", "Contribs")
_STATIC_DIR = pathjoin(_DOCS_PATH, "source_zh_CN", "contribs_static")
_OUT_INDEX_FILE = pathjoin(_OUT_DIR, "Contribs-Overview.md")

_FILENAME_MAP = {"rpsystem": "RPSystem", "xyzgrid": "XYZGrid", "awsstorage": "AWSStorage"}

# ---------------------------------------------------------------------------------------------

_FILE_STRUCTURE = """{header}
{categories}
{footer}"""

_CATEGORY_DESCS = {
    "base_systems": """
系统不一定与特定的游戏机制相关，但对整个游戏有用。例子包括登录系统、新的命令语法和构建助手。
    """,
    "full_systems": """
'完整'的游戏引擎，可以直接用于开始创建内容，无需进一步添加（除非你想要）。
""",
    "game_systems": """
游戏内的游戏玩法系统，如制作、邮件、战斗等。每个系统都可以单独采用并用于你的游戏。这不包括角色扮演特定的系统，那些在 `rpg` 类别中。
""",
    "grid": """
与游戏世界的拓扑和结构相关的系统。与房间、出口和地图构建相关的贡献。
""",
    "rpg": """
专门与角色扮演和规则实现相关的系统，如角色特征、掷骰子和表情。
""",
    "tutorials": """
专门用于教授开发概念或示例 Evennia 系统的帮助资源。任何与文档教程相关的额外资源都在这里。也是教程世界和 Evadventure 演示代码的家。
""",
    "utils": """
杂项，文本操作工具、安全审计等。
""",
}


HEADER = """# 贡献

```{{sidebar}} 更多贡献
额外的 Evennia 代码片段和贡献可以在 [社区贡献和片段][forum] 论坛中找到。
```
_贡献_ 是由 Evennia 社区贡献的可选代码片段和系统。它们的大小和复杂性各不相同，并且可能比 '核心' Evennia 更具体地针对游戏类型和风格。此页面是自动生成的，汇总了当前 Evennia 发行版中包含的所有 **{ncontribs}** 个贡献。

所有贡献类别都从 `evennia.contrib` 导入，例如

    from evennia.contrib.base_systems import building_menu

每个贡献都包含如何将其与其他代码集成的安装说明。如果你想调整贡献的代码，只需将其整个文件夹复制到你的游戏目录并从那里修改/使用即可。

如果你想添加贡献，请参阅 [贡献指南](Contribs-Guidelines)!

[forum]: https://github.com/evennia/evennia/discussions/categories/community-contribs-snippets

## 索引
{category_index}
{index}
"""


TOCTREE = """
```{{toctree}}
:hidden:
Contribs-Guidelines.md
```
```{{toctree}}
:maxdepth: 1

{listing}
```"""

CATEGORY = """
## {category}

_{category_desc}_

{toctree}

{blurbs}


"""

BLURB = """
### `{name}`

_{credits}_

{blurb}

[阅读文档](./{filename}) - [浏览代码](api:{code_location})

"""

FOOTER = """

----

<small>此文档页面生成自 `{path}`。对此文件的更改将被覆盖，因此请编辑该文件而不是此文件。</small>
"""

STATIC_FOOTER = """

----

<small>此文档页面并非由 `{path}`自动生成。如想阅读最新文档，请参阅原始README.md文件。</small>
"""

INDEX_FOOTER = """

----

<small>此文档页面是自动生成的。手动更改将被覆盖。</small>
"""


def build_table(datalist, ncols):
    """Build a Markdown table-grid for compact display"""

    nlen = len(datalist)
    table_heading = "| " * (ncols) + "|"
    table_sep = "|---" * (ncols) + "|"
    table = ""
    for ir in range(0, nlen, ncols):
        table += "| " + " | ".join(datalist[ir : ir + ncols]) + " |\n"
    return f"{table_heading}\n{table_sep}\n{table}"


def readmes2docs(directory=_SOURCE_DIR):
    """
    Parse directory for README files and convert them to doc pages.

    """

    ncount = 0
    index = []
    category_index = []
    categories = defaultdict(list)

    glob_path = f"{directory}{sep}*{sep}*{sep}README.md"

    for file_path in glob(glob_path):
        # paths are e.g. evennia/contrib/utils/auditing/README.md
        _, category, name, _ = file_path.rsplit(sep, 3)

        index.append(f"[{name}](#{name.lower()})")
        category_index.append(f"[{category}](#{category.lower()})")

        pypath = f"evennia.contrib.{category}.{name}"

        filename = (
            "Contrib-"
            + "-".join(
                _FILENAME_MAP.get(part, part.capitalize() if part[0].islower() else part)
                for part in name.split("_")
            )
            + ".md"
        )

        outfile = pathjoin(_OUT_DIR, filename)

        # If a manual translation file exists, ignore the source file from the template.
        if Path(f"{_STATIC_DIR}/{filename}").exists():
            with open(f"{_STATIC_DIR}/{filename}") as fil:
                data = fil.read()
            clean_file_path = f"evennia{sep}contrib{file_path[len(directory):]}"
            data += STATIC_FOOTER.format(path=clean_file_path)
        else:
            with open(file_path) as fil:
                data = fil.read()

            clean_file_path = f"evennia{sep}contrib{file_path[len(directory):]}"
            data += FOOTER.format(path=clean_file_path)

        try:
            credits = data.split("\n\n", 3)[1]
            blurb = data.split("\n\n", 3)[2]
        except IndexError:
            blurb = name

        with open(outfile, "w") as fil:
            fil.write(data)

        categories[category].append((name, credits, blurb, filename, pypath))
        ncount += 1

    # build the list of categories with blurbs

    category_sections = []
    for category in sorted(categories):
        filenames = []
        contrib_tups = categories[category]
        catlines = []
        for tup in sorted(contrib_tups, key=lambda tup: tup[0].lower()):
            catlines.append(
                BLURB.format(
                    name=tup[0], credits=tup[1], blurb=tup[2], filename=tup[3], code_location=tup[4]
                )
            )
            filenames.append(f"{tup[3]}")
        toctree = TOCTREE.format(listing="\n".join(filenames))
        category_sections.append(
            CATEGORY.format(
                category=category,
                category_desc=_CATEGORY_DESCS[category].strip(),
                blurbs="\n".join(catlines),
                toctree=toctree,
            )
        )

    # build the header, with two tables and a count
    header = HEADER.format(
        ncontribs=len(index),
        category_index=build_table(sorted(set(category_index)), 7),
        index=build_table(sorted(index), 5),
    )

    # build the final file

    text = _FILE_STRUCTURE.format(
        header=header, categories="\n".join(category_sections), footer=INDEX_FOOTER
    )

    with open(_OUT_INDEX_FILE, "w") as fil:
        fil.write(text)

    print(f"  -- Converted Contrib READMEs to {ncount} doc pages + index.")


if __name__ == "__main__":
    readmes2docs(_SOURCE_DIR)
