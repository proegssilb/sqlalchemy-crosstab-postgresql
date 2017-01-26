from sqlalchemy.sql import FromClause, column, ColumnElement
from sqlalchemy.orm import Query
from sqlalchemy.ext.compiler import compiles

class crosstab(FromClause):
    def __init__(self, stmt, return_def, categories=None, auto_order=True):
        if not (isinstance(return_def, (list, tuple))
                or return_def.is_selectable):
            raise TypeError('return_def must be a selectable or tuple/list')
        self.stmt = stmt
        self.columns = return_def if isinstance(return_def, (list, tuple)) \
            else return_def.columns
        self.categories = categories
        if hasattr(return_def, 'name'):
            self.name = return_def.name
        else:
            self.name = None

        if isinstance(self.stmt, Query):
            self.stmt = self.stmt.selectable
        if isinstance(self.categories, Query):
            self.categories = self.categories.selectable

        #Don't rely on the user to order their stuff
        if auto_order:
            self.stmt = self.stmt.order_by('1,2')
            if self.categories is not None:
                self.categories = self.categories.order_by('1')

    def _populate_column_collection(self):
        self._columns.update(
            column(name, type=type_)
            for name, type_ in self.names
        )

@compiles(crosstab, 'postgresql')
def visit_element(element, compiler, **kw):
    if element.categories is not None:
        return """crosstab($$%s$$, $$%s$$) AS (%s)""" % (
            compiler.visit_select(element.stmt),
            compiler.visit_select(element.categories),
            ", ".join(
                "\"%s\" %s" % (c.name, compiler.visit_typeclause(c))
                for c in element.c
                )
            )
    else:
        return """crosstab($$%s$$) AS (%s)""" % (
            compiler.visit_select(element.stmt),
            ", ".join(
                "%s %s" % (c.name, compiler.visit_typeclause(c))
                for c in element.c
                )
            )

from operator import add
from sqlalchemy import func, INTEGER

class row_total(ColumnElement):
    type = INTEGER()
    def __init__(self, cols):
        self.cols = cols

@compiles(row_total)
def compile_row_total(element, compiler, **kw):
    #coalesce_columns = [func.coalesce("'%s'" % x.name, 0) for x in element.cols]
    coalesce_columns = ['coalesce("%s", 0)' % x.name for x in element.cols]
    return "+".join(coalesce_columns)
