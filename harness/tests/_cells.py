"""Test helpers: run layout and query the emitted cells/regions by role/field."""
import random
from tablelab.layout import layout_with_regions


def placed(dc, seed=0):
    """Return (tokens, cells, regions)."""
    return layout_with_regions(dc, random.Random(seed))


def cells_where(cells, **kw):
    """Cells matching all given attributes, e.g. cells_where(cells, role='data', field='amount')."""
    return [c for c in cells if all(getattr(c, k) == v for k, v in kw.items())]


def text_of(tokens, cell):
    """The cell's words joined in token_ids order."""
    return " ".join(tokens[i].text for i in cell.token_ids)


def bg_token_ids(tokens, cells):
    """Token indices that belong to no cell (background tokens)."""
    claimed = {i for c in cells for i in c.token_ids}
    return [i for i in range(len(tokens)) if i not in claimed]
