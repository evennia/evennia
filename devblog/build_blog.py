"""
A simple tool for building the blog from markdown files. Uses Jinja2 for templating and
mistletoe for markdown->html generation.


Each blog file should be named `YYYY-MM-DD-Name-of-Post.md` It can have a header
with meta info:

```
title: Title in free form
date: Date in free form (if different from current date)
images: Image references/links in markdown format (all on one line)
---

Here starts the main text ...

```


"""

import glob
from dataclasses import dataclass
from collections import defaultdict
from dateutils import parser as dateparser
from datetime import datetime
from os.path import abspath, dirname, join as pathjoin, sep
import mistletoe
import jinja2


SOURCE_DIR = dirname(abspath(__file__))
IMG_DIR = pathjoin(SOURCE_DIR, "images")
OUTDIR = pathjoin(dirname(dirname(abspath(__file__))), "html")
TEMPLATE_DIR = pathjoin(SOURCE_DIR, "templates")

BLOG_TEMPLATE = "blog.html"
POST_TEMPLATE = "post.html"


@dataclass
class Post:
    title: str
    date: datetime
    image_refs: str
    html: str


def md2html():

    jinja_templates = jinja2.FileSystemLoader(TEMPLATE_DIR)
    jinja_env = jinja2.Environment(loader=jinja_templates)
    blog_template = jinja_env.get_template(BLOG_TEMPLATE)
    post_template = jinja_env.get_template(POST_TEMPLATE)

    calendar = defaultdict(list)
    posts = []

    for file_path in glob.glob(pathjoin(SOURCE_DIR, "*.md")):
        # parse/check if file is on form YY-MM-DD-Blog-Name.md
        filename = file_path.rsplit(sep, 1)[1] if sep in file_path else file_path
        try:
            year, month, day, title = filename.split("-", 3)
        except ValueError:
            print(f"Warning: Markdown file '{filename}' is not on a recognized format. Skipping.")
            continue

        title = title[:-3]  # remove .md ending
        date = datetime.datetime(year=year, month=month, day=day)
        image_refs = ""

        with open(file_path) as fil:
            lines = fil.readlines()

        # check if there is a meta header in the first 5 lines
        meta = None
        try:
            meta_end = [lin.strip() for lin in lines[:5]].index("---")
        except ValueError:
            pass
        else:
            meta = lines[:meta_end]
            lines = lines[meta_end + 1]
            for line in meta:
                line = line.strip()
                if line.startswith("title:"):
                    title = line.strip()[6:]
                elif line.startswith("date:"):
                    date = dateparser.parse(line)
                elif line.startswith("images"):
                    image_refs = line

        markdown_post = "\n".join(lines)
        # convert markdown to html
        html_post = mistletoe.markdown(markdown_post)

        # populate template with jinja
        context = {
            "post-title": title,
            "date": date,
            "content": html_post,
            "image-reference": image_refs
        }
        html_page = post_template.render(context)

        # store
        post = Post(title=title, date=date, image_refs=image_refs, html=html_page)
        posts.append(post)
        calendar[date.year].append(post)

    # we have all posts, now insert them into the blog

    posts = sorted(posts, key=lambda pst: -pst.date.toordinal())
    for year in calendar:
        calendar[year] = sorted(calendar[year], key=lambda pst: -pst.date.toordinal())

    context = {
        posts: posts,
        calendar: calendar
    }

    html_page = blog_template.render(context)

    return html_page


if __name__ == "__main__":
    print(md2html())
