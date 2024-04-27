from dataclasses import dataclass, field, replace
from typing import FrozenSet, Set, Dict, List, Tuple, Union
from automato import AutomatoFinito




@dataclass(frozen=True)
class RegexNode:
    nullable: bool = field(default=None, repr=False)
    firstpos: FrozenSet[int] = field(default_factory=frozenset, repr=False)
    lastpos: FrozenSet[int] = field(default_factory=frozenset, repr=False)

@dataclass(frozen=True)
class LeafNode(RegexNode):
    value: str = ""

EMPTY = LeafNode(value="")

@dataclass(frozen=True)
class CatNode(RegexNode):
    left: RegexNode = EMPTY
    right: RegexNode = EMPTY

@dataclass(frozen=True)
class OrNode(RegexNode):
    left: RegexNode = EMPTY
    right: RegexNode = EMPTY

@dataclass(frozen=True)
class StarNode(RegexNode):
    child: RegexNode = EMPTY


@dataclass
class Reader:
    value: str
    pos: str = 0

    @property
    def end(self):
        return self.pos >= len(self.value)
    
    def advance(self):
        if self.end:
            return
        
        self.pos += 1

    def read(self) -> Union[str, None]:
        if self.end:
            return None
    
        ch = self.value[self.pos]
        self.advance()

        return ch

    def peek(self) -> Union[str, None]:
        if self.end:
            return None

        return self.value[self.pos]


def parse_regex(value: str):
    """
    
    Gramática:
    ```
    alternative -> sequence | sequence '|' alternative
    sequence -> term*
    term -> factor '*'*
    factor -> char | '(' alternative ')'
    ```
    """

    return parse_alternative(Reader(value))

def parse_alternative(reader: Reader):
    node = parse_sequence(reader)

    while reader.peek() == "|":
        reader.advance()

        right = parse_sequence(reader)
        node = OrNode(left=node, right=right)

    return node

def parse_sequence(reader: Reader):
    terms: List[RegexNode] = []

    while not reader.end and reader.peek() not in (")", "|"):
        terms.append(parse_term(reader))
    
    if not terms:
        return LeafNode(value="")
    
    if len(terms) == 1:
        return terms[0]
    
    node, *terms = terms
    for other in terms:
        node = CatNode(left=node, right=other)
    
    return node

def parse_term(reader: Reader):
    node = parse_factor(reader)

    while reader.peek() == "*":
        reader.advance()
        node = StarNode(child=node)
    
    return node

def parse_factor(reader: Reader):
    if reader.peek() == "(":
        reader.advance()
        value = parse_alternative(reader)
        reader.advance()

        return value
    
    value = reader.read()

    if value == "&":
        return LeafNode(value="")

    return LeafNode(value=value if value is not None else "")


@dataclass
class AnnotationAccumulator:
    pos: int = 0
    followpos: Dict[int, Set[int]] = field(default_factory=dict)

def annotate_tree(root: RegexNode) -> Tuple[RegexNode, Dict[int, Set[int]]]:
    acc = AnnotationAccumulator()
    annotated_tree = visit_node(root, acc)

    return annotated_tree, acc.followpos

def visit_node(node: RegexNode, acc: AnnotationAccumulator) -> RegexNode:
    if isinstance(node, LeafNode):
        return visit_leaf(node, acc)
    
    if isinstance(node, StarNode):
        return visit_star(node, acc)

    if isinstance(node, OrNode):
        return visit_or(node, acc)

    if isinstance(node, CatNode):
        return visit_cat(node, acc)

def visit_leaf(node: LeafNode, acc: AnnotationAccumulator):
    if not node.value:
        return replace(
            node, nullable=True, firstpos=frozenset(), lastpos=frozenset()
        )

    acc.pos += 1
    pos = frozenset([acc.pos])

    return replace(node, nullable=False, firstpos=pos, lastpos=pos)

def visit_star(node: StarNode, acc: AnnotationAccumulator):
    child = visit_node(node.child, acc)

    firstpos = child.firstpos
    lastpos = child.lastpos

    for i in lastpos:
        positions = acc.followpos.setdefault(i, set())
        positions.update(firstpos)

    return replace(
        node,
        child=child,
        nullable=True,
        firstpos=firstpos,
        lastpos=lastpos
    )

def visit_or(node: OrNode, acc: AnnotationAccumulator):
    left = visit_node(node.left, acc)
    right = visit_node(node.right, acc)

    return replace(
        node,
        left=left,
        right=right,
        nullable=left.nullable or right.nullable,
        firstpos=left.firstpos | right.firstpos,
        lastpos=left.lastpos | right.lastpos,
    )

def visit_cat( node: CatNode, acc: AnnotationAccumulator):
    left = visit_node(node.left, acc)
    right = visit_node(node.right, acc)

    for i in left.lastpos:
        positions = acc.followpos.setdefault(i, set())
        positions.update(right.firstpos)

    return replace(
        node,
        left=left,
        right=right,
        nullable=left.nullable and right.nullable,
        firstpos=left.firstpos | right.firstpos if left.nullable else left.firstpos,
        lastpos=left.firstpos | right.firstpos if right.nullable else right.firstpos,
    )


def get_leafs(node: RegexNode) -> Tuple[LeafNode, ...]:
    if isinstance(node, LeafNode):
        return (node,) if node.value else ()

    if isinstance(node, (OrNode, CatNode)):
        return get_leafs(node.left) + get_leafs(node.right)

    if isinstance(node, StarNode):
        return get_leafs(node.child)
    
    return ()

def generate_automaton(
    annotated_tree: RegexNode, followpos: Dict[int, Set[int]]
) -> AutomatoFinito:
    leafs = get_leafs(annotated_tree)
    symbol_map = {
        i: node.value
        for node in leafs
        for i in node.firstpos
    }

    initial = annotated_tree.firstpos
    transitions = []

    states = {initial}
    remaining = {initial}

    while remaining:
        state = remaining.pop()

        destinations: Dict[str, FrozenSet[int]] = {}
        for i in state:
            symbol = symbol_map[i]
            dest = destinations.get(symbol, frozenset()) | followpos.get(i, frozenset())

            if not dest:
                continue
            destinations[symbol] = dest
        
        state_transitions = [
            (state, symbol, dest) for symbol, dest in destinations.items()
        ]
        transitions.extend(state_transitions)
        remaining.update(s for s in destinations.values() if s not in states)
        states.update(destinations.values())
    
    final_i, *_ = leafs[-1].lastpos
    finals = {state for state in states if final_i in state}

    alphabet = set(symbol for _, symbol, _ in transitions)

    format = {
        state: "{" + ",".join(str(n) for n in sorted(state)) + "}" for state in states
    }

    return AutomatoFinito(
        format[initial],
        (format[s] for s in finals),
        alphabet,
        ((format[origin], symbol, format[dest]) for origin, symbol, dest in transitions)
    )


def convert_regex(value: Union[str, RegexNode]):
    node = parse_regex(value) if isinstance(value, str) else value
    node = CatNode(left=node, right=LeafNode(value="#"))

    annotated_tree, followpos = annotate_tree(node)

    return generate_automaton(annotated_tree, followpos)