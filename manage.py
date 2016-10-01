#!/usr/bin/env python
import os
import sys

if sys.version_info.major < 3:
    raise RuntimeError('Please switch to Python 3. Python 2 is not supported.')

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tweet_d_feed.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
