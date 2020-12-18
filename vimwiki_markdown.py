#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import datetime
import os
import shutil
import subprocess
import sys

import markdown
from markdown.extensions.codehilite import CodeHiliteExtension

default_template = """<!DOCTYPE html>
<html>
    <head>
        <meta charset="UTF-8" />
        <meta name="date" content="%date%" scheme="YYYY-MM-DD">
        <meta name="viewport" content="width=device-width" />
        <title>%title%</title>
        <link rel="stylesheet" href="%root_path%style.css" type="text/css"
         media="screen" title="no title" charset="utf-8">
        <link rel="stylesheet" href="%root_path%pygmentize.css" type="text/css"
         media="screen" title="no title" charset="utf-8">
    </head>
    <body>

%content%

    </body>
</html>
"""

vim = shutil.which("vim") and "vim" or (shutil.which("nvim") and "nvim")

if vim:
    # Retrieve auto index vimwiki option
    with subprocess.Popen(
        [vim, "-c", "echo g:vimwiki_dir_link", "-c", ":q", "--headless"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ) as proc:
        auto_index = proc.stderr.read() == b"index"
else:
    auto_index = False


class LinkInlineProcessor(markdown.inlinepatterns.LinkInlineProcessor):
    """Fix wiki links"""

    def getLink(self, *args, **kwargs):
        href, title, index, handled = super().getLink(*args, **kwargs)
        if not href.startswith("http") and not href.endswith(".html"):
            if auto_index and href.endswith("/"):
                href += "index.html"
            elif not href.endswith("/"):
                href += ".html"
        return href, title, index, handled


def get(l, index, default):
    return l[index] if index < len(l) else default


def cleanArgv(argv):
    res = []
    for val in argv:
        tmp = val
        tmp = tmp[1:] \
            if tmp.startswith("'") or tmp.startswith('"') \
            else tmp
        tmp = tmp[:-1] \
            if (tmp.endswith("'") and not tmp.endswith("\\'")) \
            or (tmp.endswith('"') and not tmp.endswith('\\"')) \
            else tmp
        res.append(tmp)
    return res


def main():

    args = cleanArgv(sys.argv)

    FORCE = args[1]  # noqa - not supported
    SYNTAX = args[2]
    EXTENSION = args[3]  # noqa - not supported
    OUTPUT_DIR = args[4]
    INPUT_FILE = args[5]
    CSS_FILE = args[6]  # noqa - not supported
    TEMPLATE_PATH = get(args, 7, os.getenv("VIMWIKI_TEMPLATE_PATH", ""))
    TEMPLATE_DEFAULT = get(
        args, 8, os.getenv("VIMWIKI_TEMPLATE_DEFAULT", "")
    )
    TEMPLATE_EXT = get(args, 9, os.getenv("VIMWIKI_TEMPLATE_EXT", ""))
    ROOT_PATH = get(args, 10, os.getenv("VIMWIKI_ROOT_PATH", os.getcwd()))

    # Only markdown is supported
    if SYNTAX != "markdown":
        sys.stderr.write("Unsupported syntax: " + SYNTAX)
        sys.exit(1)

    # Asign template
    template = default_template
    template_file = (
        os.path.join(TEMPLATE_PATH, TEMPLATE_DEFAULT) + TEMPLATE_EXT
    )
    if os.path.isfile(template_file):
        with open(template_file, "rb") as f:
            template = f.read().decode()

    # Get output filename
    filename, _ = os.path.splitext(os.path.basename(INPUT_FILE))
    output_file = os.path.join(OUTPUT_DIR, filename + ".html")

    extensions = ["fenced_code", "tables"]
    extensions += os.getenv("VIMWIKI_MARKDOWN_EXTENSIONS", "").split(",")
    extensions = set([e for e in extensions if e] + [CodeHiliteExtension()])

    # Setup markdown parser
    md = markdown.Markdown(extensions=extensions)
    md.inlinePatterns.deregister("link")
    md.inlinePatterns.register(
        LinkInlineProcessor(markdown.inlinepatterns.LINK_RE, md), "link", 160
    )

    with open(INPUT_FILE, "rb") as f:
        content = ""
        placeholders = {}

        # Retrieve vimwiki placeholders
        for line in f:
            line = line.decode()[:-1]
            if line.startswith("%nohtml"):
                sys.exit(0)
            elif line.startswith("%title"):
                placeholders["%title%"] = line[7:]
            elif line.startswith("%date"):
                placeholders["%date%"] = line[6:]
            elif line.startswith("%template"):
                placeholders["template"] = line[10:]
            else:
                content += line + "\n"

        # Set default values
        if "%title%" not in placeholders:
            placeholders["%title%"] = filename
        if "%date%" not in placeholders:
            placeholders["%date%"] = datetime.datetime.today().strftime(
                "%Y-%m-%d"
            )
        if "template" in placeholders:
            t = placeholders.pop("template")
            template_file = os.path.join(TEMPLATE_PATH, t) + TEMPLATE_EXT
            if os.path.isfile(template_file):
                with open(template_file, "rb") as f:
                    template = f.read().decode()

        # Parse template
        for placeholder, value in placeholders.items():
            template = template.replace(placeholder, value)
        # use blank insted of os.getcwd() because - mean in root directory that contain css
        template = template.replace(
            "%root_path%", ROOT_PATH if ROOT_PATH != "-" else ""
        )

        # Parse content
        content = md.convert(content)

        # Merge template
        template = template.replace("%content%", content)

    with open(output_file, "wb") as o:
        o.write(template.encode())


if __name__ == "__main__":
    main()
