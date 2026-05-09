"""Minimal Django bootstrap for tests in backends/python/api.

Lets us import view modules and B24AuthContext without spinning up
a real database — the dummy ENGINE in settings.py covers everything.
"""

import os
import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parent.parent
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
os.environ.setdefault("BUILD_TARGET", "dev")
os.environ.setdefault("VIRTUAL_HOST", "https://test.example.com")
os.environ.setdefault("JWT_SECRET", "test-secret-do-not-use-in-prod-32b!!")

import django  # noqa: E402
from django.apps import apps as _apps  # noqa: E402

if not _apps.ready:
    django.setup()
