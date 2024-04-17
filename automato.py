
from dataclasses import dataclass
import re
from typing import Dict, FrozenSet, Generator, Iterable, List, Set, Tuple, Union

Estado = str
Transicao = Tuple[Estado, str, Estado]
MapaDeTransicao = Dict[Tuple[Estado, str], Set[Estado]]

Epsilon = "&"


def serializar_conjunto_de_estados(estados: Iterable[Estado]) -> str:
    # return "{" + "".join(sorted(estados)) + "}"
    return "".join(sorted(estados))

@dataclass(init=False)
class AutomatoFinito:
    estados: FrozenSet[Estado]
    estado_inicial: Estado
    estados_finais: FrozenSet[Estado]
    alfabeto: FrozenSet[str]
    mapa_transicoes: MapaDeTransicao

    def __init__(
        self,
        estado_inicial: Estado,
        estados_finais: Iterable[Estado],
        alfabeto: Iterable[str],
        transicoes: Iterable[Transicao],
    ):
        self.estados = self.pegar_estados(transicoes)
        self.estado_inicial = estado_inicial
        self.estados_finais = frozenset(estados_finais)
        self.alfabeto = frozenset(alfabeto) - {Epsilon,}
        self.mapa_transicoes = self.criar_mapa_de_transicao(transicoes)

    @classmethod
    def pegar_estados(cls, transicoes: Iterable[Transicao]) -> FrozenSet[Estado]:
        estados = set()

        for origem, _, destino in transicoes:
            estados.add(origem)
            estados.add(destino)
        
        return frozenset(estados)
    
    @classmethod
    def criar_mapa_de_transicao(cls, transicoes: Iterable[Transicao]) -> MapaDeTransicao:
        mapa: MapaDeTransicao = {}

        for origem, simbolo, destino in transicoes:
            chave = (origem, simbolo)

            estados_de_destino = mapa.setdefault(chave, set())
            estados_de_destino.add(destino)
        
        return mapa

    def transicao(self, origem: Estado, simbolo: str) -> FrozenSet[Estado]:
        chave = (origem, simbolo)
        return frozenset(self.mapa_transicoes.get(chave, set()))

    def transicoes(self) -> Generator[Transicao, None, None]:
        for (origem, simbolo), destinos in self.mapa_transicoes.items():
            for d in destinos:
                yield (origem, simbolo, d)
    
    def pegar_alcancaveis(self, estado: Estado, simbolo: Union[str, None] = None) -> FrozenSet[Estado]:
        alcancados: Set[Estado] = set([estado])
        restantes: Set[Estado] = set([estado])

        simbolos = {simbolo,} if simbolo is not None else self.alfabeto

        while restantes:
            estado = restantes.pop()

            for s in simbolos:
                destinos = self.transicao(estado, s)

                restantes.update(d for d in destinos if d not in alcancados)
                alcancados.update(destinos)
        
        return frozenset(alcancados)

    def calcular_epsilon_fecho(self):
        resultado: Dict[Estado, FrozenSet[Estado]] = {}

        for estado in self.estados:
            resultado[estado] = self.pegar_alcancaveis(estado, Epsilon)

        return resultado

    def determinizar(self) -> "AutomatoFinito":
        fecho = self.calcular_epsilon_fecho()

        conjunto_inicial = fecho[self.estado_inicial]
        inicial = serializar_conjunto_de_estados(conjunto_inicial)
        transicoes: List[Transicao] = []
        finais: Set[Estado] = set()

        visitados: Set[FrozenSet[Estado]] = set()
        restantes: Set[FrozenSet[Estado]] = set([conjunto_inicial])

        while restantes:
            conjunto_origem = restantes.pop()
            origem = serializar_conjunto_de_estados(conjunto_origem)

            if conjunto_origem in visitados:
                continue
            visitados.add(conjunto_origem)

            for simbolo in self.alfabeto:
                conjunto_destino: Set[Estado] = set()

                for estado in conjunto_origem:
                    destinos = self.transicao(estado, simbolo)

                    for destino in destinos:
                        conjunto_destino.update(estado for estado in fecho[destino])
                
                if not conjunto_destino:
                    continue

                destino = serializar_conjunto_de_estados(conjunto_destino)

                transicao: Transicao = (origem, simbolo, destino)
                transicoes.append(transicao)

                if frozenset(conjunto_destino) not in visitados:
                    restantes.add(frozenset(conjunto_destino))
            
            if any(estado in self.estados_finais for estado in conjunto_origem):
                finais.add(origem)
        
        return AutomatoFinito(inicial, finais, self.alfabeto, transicoes)

    def serializar(self) -> str:
        num_estados = len(self.estados)
        inicial = self.estado_inicial
        finais = "{" + ",".join(sorted(self.estados_finais)) + "}"
        alfabeto = "{" + ",".join(sorted(self.alfabeto)) + "}"
        transicoes = ";".join(",".join(transicao) for transicao in sorted(self.transicoes()))

        return f"{num_estados};{inicial};{finais};{alfabeto};{transicoes}"


def parse(entrada: str):
    """
        <número de estados>;<estado inicial>;{<estados finais>};{<alfabeto>};<transições>

        <estado origem>,<simbolo do alfabeto>,<estado destino>
    """

    # remove todos os espaços em branco
    entrada = re.sub(r"\s+", "", entrada)

    _, inicial, finais_str, alfabeto_str, *transicoes_str = entrada.split(";")

    finais = set(finais_str[1:-1].split(","))
    alfabeto = set(alfabeto_str[1:-1].split(","))
    transicoes = set(tuple(t.split(",")) for t in transicoes_str)

    return AutomatoFinito(inicial, finais, alfabeto, transicoes)
