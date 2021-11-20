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
import rfeed

import mistletoe
from mistletoe import HTMLRenderer, BaseRenderer
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

RSS_FEED = "feed"

CURRENT_YEAR = datetime.utcnow().year


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


def build_rss_feed(blogposts):
    """
    Create a rss feed with all blog posts.

    Args:
        blogposts: A list of `BlogPost` entries.

    """
    print("Rebuilding RSS feed ...")
    feeditems = []
    for blogpost in blogposts:
        feeditems.append(
            rfeed.Item(
                title=blogpost.title,
                link=blogpost.permalink,
                description=blogpost.blurb,
                author="Griatch",
                guid=rfeed.Guid(blogpost.permalink),
                pubDate=datetime.fromordinal(blogpost.date_sort),
            )
        )
    return rfeed.Feed(
        title="Evennia Devblog RSS Feed",
        link="https://www.evennia.com/devblog/feed.rss",
        description="""Evennia is a modern Python library and server for creating text-based
        multi-player games and virtual worlds (also known as MUD, MUSH, MU,
        MUX, MUCK, etc). While Evennia handles all the necessary things every
        online game needs, like database and networking, you create the game of
        your dreams by writing normal Python modules.""",
        language="en-US",
        lastBuildDate=datetime.utcnow(),
        items=feeditems,
    ).rss()


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

        # get first paragraph as blurb
        markdown_blurb = "\n".join(
            [line for line in lines if line and not line.startswith("!")][:3])
        markdown_post = "\n".join(lines)
        # convert markdown to html
        blurb = mistletoe.markdown(markdown_blurb, BaseRenderer)
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
    blogpostlist = []
    blogpages = []
    for year in sorted(calendar, reverse=True):
        blogposts = list(sorted(calendar[year], key=lambda post: -post.date_sort))
        blogpostlist.extend(blogposts)
        blogpages.append(
            BlogPage(
                year=year,
                permalink=OUTFILE_TEMPLATE.format(year=year),
                posts=blogposts,
                calendar=calendar
            )
        )

    # generate the rss feed
    rss_feed = build_rss_feed(blogpostlist)

    # build the html blog pages, one per year
    latest_post = blogpages[0].posts[0]
    latest_title = latest_post.title
    latest_blurb = latest_post.blurb

    html_pages = {}
    for blogpage in blogpages:
        print(f"Processing blogs from {blogpage.year} ...")

        context = {
            "latest_title": latest_title,
            "latest_blurb": latest_blurb,
            "pageyear": blogpage.year,
            "blogpage": blogpage,
            "blogpages": blogpages
        }

        html_page = blog_template.render(context)

        html_pages[blogpage.year] = html_page

    return html_pages, rss_feed

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

    html_pages, rss_feed = md2html()

    print("Writing HTML files and RSS feed ...")

    # build html files
    latest_year = -1
    latest_page = None
    for year, html_page in html_pages.items():
        filename = pathjoin(OUTDIR, OUTFILE_TEMPLATE.format(year=year))
        if year > latest_year:
            latest_year = year
            latest_page = filename.rsplit(sep, 1)[1] if sep in filename else filename
        with open(filename, 'w') as fil:
            fil.write(html_page)

    # build rss file
    with open(pathjoin(OUTDIR, RSS_FEED), 'w') as fil:
        fil.write(rss_feed)

    # link static resources and the start page
    chdir(OUTDIR)
    symlink(IMG_REL_LINK, IMG_DIR_NAME)
    symlink(latest_page, START_PAGE)

    print(f"Output HTML + RSS written to {OUTDIR}{sep}. Latest year is {latest_year}.")


if __name__ == "__main__":
    pages = md2html()
    build_pages(pages)
