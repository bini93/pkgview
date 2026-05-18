from __future__ import annotations

import json
from typing import List

from pkgview.models import Package


def render_json(packages: List[Package]) -> str:
    data = [
        {
            "name": pkg.name,
            "manager": pkg.manager,
            "version": pkg.version,
            "path": pkg.path,
            "category": pkg.category,
            "managed": pkg.is_managed,
        }
        for pkg in packages
    ]
    return json.dumps(data, indent=2, ensure_ascii=False)
