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
from dataclasses import dataclass
from collections import defaultdict
from dateutil import parser as dateparser
from datetime import datetime
from os import symlink, remove, chdir
from os.path import abspath, dirname, join as pathjoin, sep
import jinja2

import mistletoe
from mistletoe import HTMLRenderer
from pygments import highlight
from pygments.styles import get_style_by_name as get_style
from pygments.lexers import get_lexer_by_name as get_lexer, guess_lexer
from pygments.formatters.html import HtmlFormatter


CURRDIR = dirname(abspath(__file__))
SOURCE_DIR = pathjoin(CURRDIR, "markdown")
TEMPLATE_DIR = pathjoin(CURRDIR, "templates")

IMG_DIR_NAME = "images"
IMG_DIR = pathjoin(CURRDIR, "images")
IMG_REL_LINK = "_src/images"

OUTDIR = dirname(CURRDIR)
OUTFILE_TEMPLATE = "{year}.html"
OUT_IMG_DIR = "images"

START_PAGE = "index.html"

BLOG_TEMPLATE = "blog.html"
POST_TEMPLATE = "post.html"

CURRENT_YEAR = datetime.now().year


@dataclass
class BlogPost:
    """
    A single blog post.

    """
    title: str
    blurb: str
    permalink: str
    pagelink: str
    anchor: str

    date_pretty: str
    date_short: str
    date_sort: int

    image_copyrights: str
    html: str


@dataclass
class BlogPage:
    """
    Represents one year/html page of blog posts.

    """
    year: int
    permalink: str
    posts: list
    calendar: dict


class PygmentsRenderer(HTMLRenderer):
    """
    Custom syntax highlighter for misteltoe (based on
    https://github.com/miyuchina/mistletoe/blob/master/contrib/pygments_renderer.py)
    """
    formatter = HtmlFormatter()
    formatter.noclasses = True

    def __init__(self, *extras, style='default'):
        super().__init__(*extras)
        self.formatter.style = get_style(style)

    def render_block_code(self, token):
        code = token.children[0].content
        lexer = get_lexer(token.language) if token.language else guess_lexer(code)
        return highlight(code, lexer, self.formatter)


def md2html():
    """
    Generate all blog pages, with one page per year.

    """

    jinja_templates = jinja2.FileSystemLoader(TEMPLATE_DIR)
    jinja_env = jinja2.Environment(loader=jinja_templates)
    blog_template = jinja_env.get_template(BLOG_TEMPLATE)
    post_template = jinja_env.get_template(POST_TEMPLATE)

    calendar = defaultdict(list)

    for file_path in glob.glob(pathjoin(SOURCE_DIR, "*.md")):
        # parse/check if file is on form YY-MM-DD-Blog-Name.md
        filename = file_path.rsplit(sep, 1)[1] if sep in file_path else file_path
        try:
            year, month, day, title = filename.split("-", 3)
        except ValueError:
            print(f"Warning: Markdown file '{filename}' is not on a recognized format. Skipping.")
            continue

        title = title[:-3]  # remove .md ending
        blurb = title[:11] + "..."
        title = " ".join(title.split("-"))
        date = datetime(year=int(year), month=int(month), day=int(day))
        image_copyrights = ""

        with open(file_path) as fil:
            lines = fil.readlines()

        # check if there is a meta header in the first 6 lines
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
                elif line.startswith("blurb:"):
                    blurb = line[6:].strip()

        markdown_post = "\n".join(lines)
        # convert markdown to html
        html = mistletoe.markdown(markdown_post, PygmentsRenderer)

        # build the permalink
        anchor = "{}".format(
            date.strftime("%Y-%m-%d-" + "-".join(title.strip().lower().split()))
        )
        pagelink = OUTFILE_TEMPLATE.format(year=date.year)
        permalink = "{}#{}".format(pagelink, anchor)

        blogpost = BlogPost(
            title=title,
            blurb=blurb,
            permalink=permalink,
            pagelink=pagelink,
            anchor=anchor,
            date_pretty=date.strftime("%B %e, %Y"),
            date_short=date.strftime("%b %e"),
            date_sort=date.toordinal(),
            image_copyrights=image_copyrights,
            html=html
        )
        # populate template with jinja and readd to blogpost
        context = {
            "blogpost": blogpost
        }
        blogpost.html = post_template.render(context)

        # store
        calendar[date.year].append(blogpost)

    # make sure to sort all entries by date
    blogpages = []
    for year in sorted(calendar, reverse=True):
        blogpages.append(
            BlogPage(
                year=year,
                permalink=OUTFILE_TEMPLATE.format(year=year),
                posts=list(sorted(calendar[year], key=lambda post: -post.date_sort)),
                calendar=calendar
            )
        )

    # build the blog pages, per year
    html_pages = {}
    for blogpage in blogpages:
        print(f"Processing blogs from {blogpage.year} ...")

        context = {
            "pageyear": blogpage.year,
            "blogpage": blogpage,
            "blogpages": blogpages
        }

        html_page = blog_template.render(context)

        html_pages[blogpage.year] = html_page

    return html_pages


def build_pages(blog_pages):
    """
    Generate devblog pages.

    """

    for html_file in glob.glob(pathjoin(OUTDIR, "*.html")):
        remove(html_file)
    try:
        remove(pathjoin(OUTDIR, START_PAGE))
    except FileNotFoundError:
        pass
    try:
        remove(pathjoin(OUTDIR, IMG_DIR_NAME))
    except FileNotFoundError:
        pass

    html_pages = md2html()

    latest_year = -1
    latest_page = None
    for year, html_page in html_pages.items():
        filename = pathjoin(OUTDIR, OUTFILE_TEMPLATE.format(year=year))
        if year > latest_year:
            latest_year = year
            latest_page = filename.rsplit(sep, 1)[1] if sep in filename else filename
        with open(filename, 'w') as fil:
            fil.write(html_page)

    chdir(OUTDIR)
    symlink(IMG_REL_LINK, IMG_DIR_NAME)
    symlink(latest_page, START_PAGE)

    print(f"Output htmls written to {OUTDIR}{sep}. Latest year is {latest_year}.")


if __name__ == "__main__":
    pages = md2html()
    build_pages(pages)
