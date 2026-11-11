"""Reserve newly requested output paths; never overwrite an existing file.

Plotters may write only the reserved paths. A failed run removes its own new
reservations; paths that existed before the call are never touched.
"""
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def new_outputs(*paths):
    resolved = [Path(p).resolve() for p in paths]
    if len(set(resolved)) != len(resolved):
        raise ValueError('输出路径须各不相同')
    created = []
    try:
        for p in resolved:
            with p.open('xb'):
                pass
            created.append(p)
        yield
    except BaseException:
        for p in created:
            p.unlink(missing_ok=True)
        raise
