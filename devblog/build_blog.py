#! /usr/bin/python

"""
A simple tool for building the blog from markdown files. Uses Jinja2 for templating and
mistletoe for markdown->html generation.


Each blog file should be named `YYYY-MM-DD-Name-of-Post.md` It can have a header
with meta info:

```
title: Title in free form
date: Date in free form (if different from current date)
copyrights: Image references/links in markdown format (all on one line)
---

Here starts the main text ...

```


"""

import glob
import shutil
from dataclasses import dataclass
from collections import defaultdict
from dateutil import parser as dateparser
from datetime import datetime
from os import mkdir, symlink
from os.path import abspath, dirname, join as pathjoin, sep
import mistletoe
import jinja2


CURRDIR = dirname(abspath(__file__))
SOURCE_DIR = pathjoin(CURRDIR, "source")
TEMPLATE_DIR = pathjoin(CURRDIR, "templates")
IMG_DIR = pathjoin(SOURCE_DIR, "images")

OUTDIR = pathjoin(CURRDIR, "html")
OUTFILE_TEMPLATE = "devblog{year}.html"
OUT_IMG_DIR = pathjoin(OUTDIR, "images")

START_PAGE = "index.html"
BLOG_TEMPLATE = "blog.html"
POST_TEMPLATE = "post.html"

CURRENT_YEAR = datetime.now().year


@dataclass
class Post:
    title: str
    permalink: str
    anchor: str

    date_pretty: str
    date_short: str
    date_sort: int

    image_copyrights: str
    html: str


def md2html():
    """
    Generate all blog pages, with one page per year.

    """

    jinja_templates = jinja2.FileSystemLoader(TEMPLATE_DIR)
    jinja_env = jinja2.Environment(loader=jinja_templates)
    blog_template = jinja_env.get_template(BLOG_TEMPLATE)
    post_template = jinja_env.get_template(POST_TEMPLATE)

    pages = {}
    calendar = defaultdict(list)

    for file_path in glob.glob(pathjoin(SOURCE_DIR, "*.md")):
        # parse/check if file is on form YY-MM-DD-Blog-Name.md
        filename = file_path.rsplit(sep, 1)[1] if sep in file_path else file_path
        try:
            year, month, day, title = filename.split("-", 3)
        except ValueError:
            print(f"Warning: Markdown file '{filename}' is not on a recognized format. Skipping.")
            continue

        print(f"Processing {filename}...")

        title = title[:-3]  # remove .md ending
        date = datetime(year=int(year), month=int(month), day=int(day))
        image_copyrights = ""

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
            lines = lines[meta_end + 1:]
            for line in meta:
                line = line.strip()
                if line.startswith("title:"):
                    title = line.strip()[6:]
                elif line.startswith("date:"):
                    date = dateparser.parse(line[5:])
                elif line.startswith("copyrights:"):
                    image_copyrights = line[12:]
                    image_copyrights = mistletoe.markdown(image_copyrights)

        markdown_post = "\n".join(lines)
        # convert markdown to html
        html = mistletoe.markdown(markdown_post)

        # build the permalink
        anchor = "{}".format(
            date.strftime("%Y-%m-%d-" + "-".join(title.strip().lower().split()))
        )
        permalink = "{}#{}".format(
            OUTFILE_TEMPLATE.format(year=date.year),
            anchor
        )
        post = Post(
            title=title,
            permalink=permalink,
            anchor=anchor,
            date_pretty=date.strftime("%B %e, %Y"),
            date_short=date.strftime("%B %e"),
            date_sort=date.toordinal(),
            image_copyrights=image_copyrights,
            html=html
        )
        # populate template with jinja
        context = {
            "post": post
        }
        post.html = post_template.render(context)

        # store
        calendar[date.year].append(post)

    # make sure to sort all entries by date
    for year in calendar:
        calendar[year] = list(sorted(calendar[year], key=lambda post: -post.date_sort))

    # pair pages with years/filenames
    for year, posts in calendar.items():

        context = {
            "page_year": year,
            "posts": posts,
            "calendar": calendar
        }

        html_page = blog_template.render(context)

        pages[year] = html_page

    return pages


def build_pages(blog_pages):
    """
    Generate devblog pages.

    """
    shutil.rmtree(OUTDIR, ignore_errors=True)
    mkdir(OUTDIR)
    mkdir(OUT_IMG_DIR)
    html_pages = md2html()

    latest_year = -1
    latest_page = None
    for year, html_page in html_pages.items():
        filename = pathjoin(OUTDIR, OUTFILE_TEMPLATE.format(year=year))
        if year > latest_year:
            latest_year = year
            latest_page = filename
        with open(filename, 'w') as fil:
            fil.write(html_page)

    shutil.copytree(IMG_DIR, OUT_IMG_DIR, dirs_exist_ok=True)
    symlink(latest_page, pathjoin(OUTDIR, START_PAGE))

    print(f"Output written to {OUTDIR}. Latest year is {latest_year}.")


if __name__ == "__main__":
    pages = md2html()
    build_pages(pages)
