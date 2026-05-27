"""Vercel serverless entry point for ZenCV.

Vercel's @vercel/python runtime looks for a WSGI callable named `app` (or
`handler`) in the file pointed to by routes. We just re-export the Flask app
created in app.py at the project root.
"""

import os
import sys

# Make the project root importable when running inside Vercel's function dir.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app import app  # noqa: E402,F401  (Vercel imports this `app`)
