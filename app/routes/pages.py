# Group "pages routes" using a Blueprint.
# A *page route* returns HTML rendered from a template.

from flask import Blueprint, render_template

# Create the blueprint for pages.
bp = Blueprint("pages", __name__)


@bp.get("/")
def home():
    """
    Home page.
    Show the habit list, add form, and mini stats.
    """

    # The template will set <body data-page="home"> so JS knows what to init.
    return render_template("index.html", page="home")


@bp.get("/progress")
def progress():
    """
    Progress page.
    Show streaks and recent activity.
    """

    return render_template("progress.html", page="progress")


@bp.get("/garden")
def garden():
    """
    Garden page.
    Will read 'currency' and serve to display/build the garden.
    """

    return render_template("garden.html", page="garden")
