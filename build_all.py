# build_all.py
# -*- coding: utf-8 -*-
"""Kör hela kedjan lokalt/i CI: data → standings → samlad app."""

import sys
import fetch_data
import fetch_standings
import build_apps


def main():
    fetch_data.main()
    fetch_standings.main()
    build_apps.main()
    return 0


if __name__ == "__main__":
    sys.exit(main())
