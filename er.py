from dataclasses import dataclass, replace

from automato import AutomatoFinito


@dataclass(frozen=True, kw_only=True)
class RegexNode:
    nullable: bool = False
    firstpos: frozenset[int] = frozenset()
    lastpos: frozenset[int] = frozenset()

@dataclass(frozen=True, kw_only=True)
class CatNode(RegexNode):
    left: RegexNode
    right: RegexNode

@dataclass(frozen=True, kw_only=True)
class OrNode(RegexNode):
    left: RegexNode
    right: RegexNode

@dataclass(frozen=True, kw_only=True)
class StarNode(RegexNode):
    child: RegexNode

@dataclass(frozen=True, kw_only=True)
class LeafNode(RegexNode):
    value: str


# (a | b)*abb
regex = CatNode(
    left=CatNode(
        left=CatNode(
            left=StarNode(
                child=OrNode(
                    left=LeafNode(value="a"),
                    right=LeafNode(value="b"),
                )
            ),
            right=LeafNode(value="a")
        ),
        right=LeafNode(value="b")
    ),
    right=LeafNode(value="b")
)
regex2 = CatNode(
    left=OrNode(left=LeafNode(value="b"),right=LeafNode(value="")),
    right=OrNode(left=LeafNode(value="a"),right=LeafNode(value=""))
)


class TreeAnnotator:
    pos: int

    def __init__(self):
        self.pos = 0

    def annotate(self, node: RegexNode):
        self.pos = 0
        return self.visit(node)
    
    def visit(self, node: RegexNode) -> RegexNode:
        if isinstance(node, LeafNode):
            return self.visit_leaf(node)
        
        if isinstance(node, StarNode):
            return self.visit_star(node)

        if isinstance(node, OrNode):
            return self.visit_or(node)

        if isinstance(node, CatNode):
            return self.visit_cat(node)

    def visit_leaf(self, node: LeafNode):
        if not node.value:
            return replace(
                node, nullable=True, firstpos=frozenset(), lastpos=frozenset()
            )

        self.pos += 1
        pos = frozenset([self.pos])

        return replace(node, nullable=False, firstpos=pos, lastpos=pos)

    def visit_star(self, node: StarNode):
        child = self.visit(node.child)

        return replace(
            node,
            child=child,
            nullable=True,
            firstpos=child.firstpos,
            lastpos=child.lastpos
        )

    def visit_or(self, node: OrNode):
        left = self.visit(node.left)
        right = self.visit(node.right)

        return replace(
            node,
            left=left,
            right=right,
            nullable=left.nullable or right.nullable,
            firstpos=left.firstpos | right.firstpos,
            lastpos=left.lastpos | right.lastpos,
        )

    def visit_cat(self, node: CatNode):
        left = self.visit(node.left)
        right = self.visit(node.right)

        return replace(
            node,
            left=left,
            right=right,
            nullable=left.nullable and right.nullable,
            firstpos=left.firstpos | right.firstpos if left.nullable else left.firstpos,
            lastpos=left.firstpos | right.firstpos if right.nullable else right.firstpos,
        )


def calculate_followpos(
    node: RegexNode,
    *,
    acc: dict[int, set[int]] | None = None
) -> dict[int, set[int]]:
    if acc is None:
        acc = {}
    
    if isinstance(node, CatNode):
        calculate_followpos(node.left, acc=acc)
        calculate_followpos(node.right, acc=acc)
        
        for i in node.left.lastpos:
            positions = acc.setdefault(i, set())
            positions.update(node.right.firstpos)
    elif isinstance(node, StarNode):
        calculate_followpos(node.child, acc=acc)

        for i in node.lastpos:
            positions = acc.setdefault(i, set())
            positions.update(node.firstpos)
    elif isinstance(node, OrNode):
        calculate_followpos(node.left, acc=acc)
        calculate_followpos(node.right, acc=acc)
    
    return acc


def get_leafs(node: RegexNode) -> tuple[LeafNode, ...]:
    if isinstance(node, LeafNode):
        return (node,) if node.value else ()

    if isinstance(node, (OrNode, CatNode)):
        return get_leafs(node.left) + get_leafs(node.right)

    if isinstance(node, StarNode):
        return get_leafs(node.child)
    
    return ()

def generate_automaton(
    annotated_tree: RegexNode, followpos: dict[int, set[int]]
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

        destinations: dict[str, frozenset[int]] = {}
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
        state: f"q{i}" for i, state in enumerate(states)
    }

    return AutomatoFinito(
        format[initial],
        (format[s] for s in finals),
        alphabet,
        ((format[origin], symbol, format[dest]) for origin, symbol, dest in transitions)
    )


def convert_regex(node: RegexNode):
    node = CatNode(left=node, right=LeafNode(value="#"))

    annotator = TreeAnnotator()
    annotated_tree = annotator.annotate(node)

    followpos = calculate_followpos(annotated_tree)

    return generate_automaton(annotated_tree, followpos)