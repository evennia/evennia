"""
This is a little routine for viewing the sql queries that are executed by a given
query as well as count them for optimization testing.

"""

import sys
import os

# sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
# os.environ["DJANGO_SETTINGS_MODULE"] = "game.settings"
from django.db import connection


def count_queries(exec_string, setup_string):
    """
    Display queries done by exec_string. Use setup_string
    to setup the environment to test.
    """

    exec(setup_string)

    num_queries_old = len(connection.queries)
    exec(exec_string)
    nqueries = len(connection.queries) - num_queries_old

    for query in connection.queries[-nqueries if nqueries else 1 :]:
        print(query["time"], query["sql"])
    print("Number of queries: %s" % nqueries)


if __name__ == "__main__":

    # setup tests here

    setup_string = """
from evennia.objects.models import ObjectDB
g = ObjectDB.objects.get(db_key="Griatch")
"""
    exec_string = """
g.tags.all()
"""
    count_queries(exec_string, setup_string)
