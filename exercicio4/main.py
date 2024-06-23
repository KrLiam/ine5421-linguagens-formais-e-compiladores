
from dataclasses import dataclass
import re
from typing import Any, Dict, FrozenSet, Iterable, List, Set, Tuple

MSG_GRAMATICA_RECURSIVA = r"""
                                                -----
                                              /      \ 
                                              )      |
       :================:                      \"    )/
      /||  Gramática   ||                      )_ /*
     / || Recursiva a  ||                          *
    |  ||  Esquerda    ||                   (=====~*~======)
     \ ||     :(       ||                  0      \ /       0
       ==================                //   (====*====)   ||
........... /      \.............       //         *         ||
:\        ############            \    ||    (=====*======)  ||
: ---------------------------------     V          *          V
: |  *   |__________|| ::::::::::  |    o   (======*=======) o
\ |      |          ||   .......   |    \\         *         ||
  --------------------------------- 8   ||   (=====*======)  //
                                     8   V         *         V
  --------------------------------- 8   =|=;  (==/ * \==)   =|=
  \   ###########################  \   / ! \     _ * __    / | \ 
   \  +++++++++++++++++++++++++++   \  ! !  !  (__/ \__)  !  !  !
    \ ++++++++++++++++++++++++++++   \        0 \ \V/ / 0
     \________________________________\     ()   \o o/   ()
      *********************************     ()           ()
))"""

class GrammarException(Exception):
    ...


def is_terminal(symbol: str) -> bool:
    return not symbol.isupper()


@dataclass(init=False)
class Grammar:
    rule_map: Dict[str, List[str]]
    initial: str

    def __init__(self, rules: Iterable[Tuple[str, str]]):
        self.rule_map = {}
        self.initial, _ = rules[0]
        
        for head, body in rules:
            sequences = self.rule_map.setdefault(head, [])
            sequences.append(body)

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
    def terminals(self) -> Tuple[str]:
        symbols = []
        
        for sequences in self.rule_map.values():
            for sequence in sequences:
                for s in sequence:
                    if is_terminal(s) and s not in symbols:
                        symbols.append(s)
        
        if "&" in symbols:
            symbols.remove("&")

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

    def get_follow(self, non_terminal: str, search_stack: Tuple[str, ...] = ()) -> FrozenSet[str]:
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
    
    def get_left_recursive_cycle(self):
        stacks: List[Tuple[str, ...]] = []

        stacks.append((self.initial,))

        while stacks:
            nonterminal_stack = stacks.pop()

            head = nonterminal_stack[-1]
            bodies = self.get_body(head)

            for body in bodies:
                for symbol in body:
                    if is_terminal(symbol):
                        break
                                        
                    if symbol in nonterminal_stack:
                        return (*nonterminal_stack, symbol)
                    
                    next_stack = (*nonterminal_stack, symbol)
                    if next_stack not in next_stack:
                        stacks.append(next_stack)

                    if "&" not in self.get_first(symbol):
                        break

        return False
    
    def get_left_ambiguity(self):
        for head in self.nonterminals:
            bodies = self.get_body(head)

            for i, a in enumerate(bodies):
                for b in bodies[i+1:]:
                    first_intersection = (self.get_first(a) & self.get_first(b)) - {"&"}
                    if first_intersection:
                        return (head, (a, b), first_intersection)

    def generate_ll_table(self):
        if cycle := self.get_left_recursive_cycle():
            raise GrammarException(f"Gramática recursiva a esquerda: " + " => ".join(cycle))

        if ambiguity := self.get_left_ambiguity():
            head, (a, b), symbols = ambiguity
            raise GrammarException(f"Gramática não fatorada. Ambiguidade entre regras {head} => {a} e {head} => {b} pelo símbolo(s) {','.join(symbols)}.")
        
        table: Dict[Tuple[str, str], int] = {}

        follow = {symbol: self.get_follow(symbol) for symbol in self.nonterminals}

        for i, (head, body) in enumerate(self.rules):
            symbols = self.get_first(body)

            if "&" in symbols:
                symbols = (symbols | follow[head])  - {"&"}
            
            for symbol in symbols:
                table[(head, symbol)] = i + 1
            
        return table


def parse_grammar(input: str):
    input = re.sub("\s", "", input)

    rules_str = input.split(";")
    rules = [tuple(r.split("=")) for r in rules_str if r]

    return Grammar(rules)


def format_set(value: Iterable[Any]) -> str:
    value_set = set(value)
    alpha = sorted(el for el in value_set if str(el).isalpha())

    ordered = alpha + list(value_set - set(alpha))
    return "{" + ",".join(str(el) for el in ordered) + "}"


def format_ll_table(table: Dict[Tuple[str, str], int]) -> str:
    (initial, _), *_ = table.keys()
    nonterminals = format_set(t for t, _ in table.keys())
    terminals = format_set(s for _, s in table.keys())
    entries = "".join(
        sorted(
            (f"[{t},{a},{i}]" for (t, a), i in table.items()),
            key=lambda v: (ord(v[1]), ord(v[3]) + ord("z") * (not v[3].isalnum()) )
        )
    )

    return ";".join((nonterminals, initial, terminals, entries))


if __name__ == "__main__":
    entrada = input()
    grammar = parse_grammar(entrada)

    try:
        table = grammar.generate_ll_table()
        saida = format_ll_table(table)
        print(saida)
    except GrammarException as exc:
        print(exc)
