#!/usr/bin/env python

import sys

import whoosh.qparser
import whoosh.qparser.plugins
import whoosh.qparser.syntax
import whoosh.query


HANDLERS = {}


'''
Need handlers for:
Prefix

Need magic for:
yes/no's to integer fields
dates/datewords to timestamps?

Need to restrict out (sanely):
Wildcards (non-prefix)

Add support for pushing schema into place, to allow pre-fixing "bad" fields

'''


def handler(classes):
    def decorator(fn):
        for cls in classes:
            if cls in HANDLERS:
                raise ValueError("%s already has a handler")
            HANDLERS[cls] = fn
        return fn
    return decorator


@handler((whoosh.query.Term, whoosh.query.Phrase))
def build_field(clause):
    int_field = getattr(clause, "integer_field", False)
    yield "(field "
    yield clause.fieldname
    yield " "
    if not int_field:
        yield "'"
    if isinstance(clause, whoosh.query.Term):
        yield clause.text
    elif isinstance(clause, whoosh.query.Phrase):
        for word in clause.words[:-1]:
            yield word
            yield " "
        yield clause.words[-1]
    if not int_field:
        yield "'"
    yield ")"


@handler((whoosh.query.And, whoosh.query.Or, whoosh.query.Not))
def build_grouper(clause):
    yield "("
    yield clause.__class__.__name__.lower()
    for child_clause in clause.children():
        yield " "
        for piece in walk_clause(child_clause):
            yield piece
    yield ")"


@handler((whoosh.query.AndNot,))
def build_compound(clause):
    yield '(and '
    use, avoid = list(clause.children())
    for piece in walk_clause(use):
        yield piece
    yield ' (not '
    for piece in walk_clause(avoid):
        yield piece
    yield '))'


def walk_clause(clause):
    handler_fn = HANDLERS[clause.__class__]
    for piece in handler_fn(clause):
        yield piece


class IntNode(whoosh.qparser.syntax.WordNode):
    integer_field = True
    def __init__(self, value):
        self.__int_value = int(value)
        whoosh.qparser.syntax.WordNode.__init__(self, str(self.__int_value))


class IntNodePlugin(whoosh.qparser.plugins.PseudoFieldPlugin):
    def __init__(self, fieldnames):
        mapping = dict.fromkeys(fieldnames, self.modify_node)
        super(IntNodePlugin, self).__init__(mapping)
    
    @staticmethod
    def modify_node(node):
        print "INP handling", node
        import pdb; pdb.set_trace()
        if node.has_text:
            try:
                print 'returning', IntNode(node.text)
                return IntNode(node.text)
            except ValueError as e:
                print 'failing! ', e
                return None
        else:
            return node


class YesNoPlugin(IntNodePlugin):
    @staticmethod
    def modify_node(node):
        print "YNP handling", node
        if node.has_text:
            if node.text in ("yes", "y", "1"):
                print "returning", IntNode(1)
                return IntNode(1)
            else:
                print "returning", IntNode(0)
                return IntNode(0)
        else:
            print "returning", node
            return node


DEFAULT_PLUGINS = (
                   whoosh.qparser.plugins.WhitespacePlugin(),
                   whoosh.qparser.plugins.SingleQuotePlugin(),
                   whoosh.qparser.plugins.FieldsPlugin(),
                   whoosh.qparser.plugins.PrefixPlugin(),
                   whoosh.qparser.plugins.GroupPlugin(),
                   whoosh.qparser.plugins.OperatorsPlugin(AndMaybe=None,
                                                          Require=None),
                   whoosh.qparser.plugins.EveryPlugin(),
                   whoosh.qparser.plugins.PlusMinusPlugin(),
                   )


def make_parser(default_field='text', plugins=DEFAULT_PLUGINS, schema=None,
                int_fields=None, yesno_fields=None):
    parser = whoosh.qparser.QueryParser(default_field, schema, plugins=plugins)
    if int_fields is None:
        parser.add_plugin(IntNodePlugin(["count", "number"]))
    else:
        parser.add_plugin(IntNodePlugin(int_fields))
    if yesno_fields is None:
        parser.add_plugin(YesNoPlugin(["is_active", "is_ready"]))
    else:
        parser.add_plugin(YesNoPlugin(yesno_fields))
    return parser


def convert(query):
    parser = make_parser()
    parsed = parser.parse(query)
    pieces = walk_clause(parsed)
    return ''.join(pieces)


TESTS = [
         # basic fields
         ("foo", "(field text 'foo')"),
         ("foo:bar", "(field foo 'bar')"),
         
         # phrases
         ('"foo bar baz"', "(field text 'foo bar baz')"),
         
         # AND clauses
         ("foo AND bar", "(and (field text 'foo') (field text 'bar'))"),
         ("foo AND bar:baz", "(and (field text 'foo') (field bar 'baz'))"),
         
         # OR clauses
         ("foo OR bar", "(or (field text 'foo') (field text 'bar'))"),
         ("bar:baz OR foo", "(or (field bar 'baz') (field text 'foo'))"),
         
         # NOT clauses
         ("NOT foo", "(not (field text 'foo'))"),
         ("baz NOT bar", "(and (field text 'baz') (not (field text 'bar')))"),
         ("foo:bar NOT foo:baz", "(and (field foo 'bar') (not (field foo 'baz')))"),
         ("bar AND foo:-baz", )
         ]


def run_tests():
    '''because why bother with the stdlib testing library, anyway?'''
    for input_, output in TESTS:
        print input_, 'becomes', output, "? ... "
        result = convert(input_)
        try:
            assert result == output
        except AssertionError:
            print "\tnope:", result
            raise
        print "\tyup!"


def main(args):
    '''For command line testing'''
    query = ' '.join(args[1:])
    print "Lucene input:", query
    parser = make_parser()
    parsed = parser.parse(query)
    print "Parsed representation:", repr(parsed)
    print "Lucene form:", str(parsed)
    cloudsearch_query = ''.join(walk_clause(parsed))
    print "Cloudsearch form:", cloudsearch_query


if __name__ == '__main__':
    if sys.argv[1] == '--test':
        run_tests()
    else:
        main(sys.argv)
