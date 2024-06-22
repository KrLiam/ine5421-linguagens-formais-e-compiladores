
"""
First(B) = {f,n,t,(};
First(V) = {a,&};
First(A) = {f,n,t,(};
First(Z) = {o,&};
First(S) = {f,n,t,(};

Follow(S) = {$,)};
Follow(Z) = {$,)};
Follow(A) = {o,$,)};
Follow(V) = {o,$,)};
Follow(B) = {a,o,$,)};

S = S or A; S = A; A = A and B; A = B; B = not B; S = (S); S = true; S = false;
"""

from dataclasses import dataclass
import re
from typing import Any, Dict, FrozenSet, Iterable, Set, Tuple


def is_terminal(symbol: str) -> bool:
    return not symbol.isupper()

@dataclass(init=False)
class Grammar:
    rule_map: Dict[str, Set[str]]
    initial: str

    def __init__(self, rules: Iterable[Tuple[str, str]]):
        self.rule_map = {}
        self.initial, _ = rules[0]
        
        for head, body in rules:
            sequences = self.rule_map.setdefault(head, set())
            sequences.add(body)

    @property
    def nonterminals(self) -> Tuple[str]:
        symbols = []
        
        symbols.extend(head for head in self.rule_map.keys() if head not in symbols)

        for sequences in self.rule_map.values():
            for sequence in sequences:
                for s in sequence:
                    if not is_terminal(s) and s not in symbols:
                        symbols.append(s)

        return tuple(symbols)

    @property
    def rules(self) -> Iterable[Tuple[str, str]]:
        for head, body in self.rule_map.items():
            for sequence in body:
                yield (head, sequence)

    def get_body(self, non_terminal: str) -> Tuple[str, ...]:
        return tuple(self.rule_map.get(non_terminal, ()))
    
    def get_first(self, sequence: str, search_stack: Tuple[str, ...] = ()) -> FrozenSet[str]:
        first_set = set()

        for symbol in sequence:
            if is_terminal(symbol):
                symbol_first_set = {symbol,}
            else:
                bodies = self.get_body(symbol)
                first_of_bodies = [
                    self.get_first(body, (body[0], *search_stack))
                    for body in bodies if body[0] not in search_stack
                ]
                symbol_first_set = set(s for first in first_of_bodies for s in first)

            first_set.update(symbol_first_set)

            if "&" not in symbol_first_set:
                break
    
        return frozenset(first_set)

    def get_follow(self, non_terminal: str, search_stack: Tuple[str, ...] = ()) -> Tuple[str, ...]:
        follow_set = set()

        if non_terminal == self.initial:
            follow_set.add("$")
        
        for head, sequence in self.rules:
            for i, symbol in enumerate(sequence):
                if symbol == non_terminal:
                    rightside = sequence[i+1:]
                    rightside_first = self.get_first(rightside)

                    if rightside:
                        follow_set.update(rightside_first)

                    if not rightside or "&" in rightside_first:
                        if head not in search_stack:
                            follow_set.update(self.get_follow(head, (*search_stack, head)))
        
        return follow_set - {"&"}

def parse_grammar(input: str):
    input = re.sub("\s", "", input)

    rules_str = input.split(";")
    rules = [tuple(r.split("=")) for r in rules_str if r]

    return Grammar(rules)


def format_set(value: Set[Any]) -> str:
    alpha = sorted(el for el in value if str(el).isalpha())

    ordered = alpha + list(value - set(alpha))
    return "{" + ", ".join(str(el) for el in ordered) + "}"

if __name__ == "__main__":
    grammar_str = input()
    grammar = parse_grammar(grammar_str)

    saida = "; ".join([
        *(f"First({symbol}) = {format_set(grammar.get_first(symbol))}" for symbol in grammar.nonterminals),
        *(f"Follow({symbol}) = {format_set(grammar.get_follow(symbol))}" for symbol in grammar.nonterminals),
    ])
    print(saida)
