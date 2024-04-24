
from dataclasses import dataclass
import re
from typing import Dict, FrozenSet, Generator, Iterable, List, Set, Tuple, Union


Estado = str
Transicao = Tuple[Estado, str, Estado]
MapaDeTransicao = Dict[Tuple[Estado, str], Set[Estado]]

Epsilon = "&"


def unir_estados(estados: Iterable[Estado]) -> str:
    """Retorna a representação em string de um conjunto de estados."""

    return "{" + "".join(sorted(estados)) + "}"

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
        """Pega os estados utilizados em um conjunto de transições."""

        estados = set()

        for origem, _, destino in transicoes:
            estados.add(origem)
            estados.add(destino)
        
        return frozenset(estados)
    
    @classmethod
    def criar_mapa_de_transicao(cls, transicoes: Iterable[Transicao]) -> MapaDeTransicao:
        """
        Cria um dicionário que mapeia um par de estado e
        símbolo de leitura para um estado de destino.
        """

        mapa: MapaDeTransicao = {}

        for origem, simbolo, destino in transicoes:
            chave = (origem, simbolo)

            estados_de_destino = mapa.setdefault(chave, set())
            estados_de_destino.add(destino)
        
        return mapa

    def transicao(self, origem: Estado, simbolo: str) -> FrozenSet[Estado]:
        """Retorna o estado de destino dado um estado de origem e um símbolo de leitura."""

        chave = (origem, simbolo)
        return frozenset(self.mapa_transicoes.get(chave, set()))

    def transicoes(self) -> Generator[Transicao, None, None]:
        """Retorna um gerador que percorre as transições do autômato."""

        for (origem, simbolo), destinos in self.mapa_transicoes.items():
            for d in destinos:
                yield (origem, simbolo, d)
    
    def pegar_alcancaveis(self, estado: Estado, simbolo: Union[str, None] = None) -> FrozenSet[Estado]:
        """
        Realiza uma busca em largura a partir de um estado considerando apenas
        transições que leem o símbolo especificado, retornando os estados alcançados.
        Se nenhum símbolo é especificado, considera todas as transições disponívies.
        """

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
        """
        Calcula os estados alcançados por epsilon para todos os estados do autômato.
        """

        resultado: Dict[Estado, FrozenSet[Estado]] = {}

        for estado in self.estados:
            resultado[estado] = self.pegar_alcancaveis(estado, Epsilon)

        return resultado

    def determinizar(self) -> "AutomatoFinito":
        """Retorna o autômato finito determinístico equivalente."""

        fecho = self.calcular_epsilon_fecho()

        conjunto_inicial = fecho[self.estado_inicial]
        inicial = unir_estados(conjunto_inicial)
        transicoes: List[Transicao] = []
        finais: Set[Estado] = set()

        visitados: Set[FrozenSet[Estado]] = set()
        restantes: Set[FrozenSet[Estado]] = set([conjunto_inicial])

        while restantes:
            conjunto_origem = restantes.pop()
            origem = unir_estados(conjunto_origem)

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

                destino = unir_estados(conjunto_destino)

                transicao: Transicao = (origem, simbolo, destino)
                transicoes.append(transicao)

                if frozenset(conjunto_destino) not in visitados:
                    restantes.add(frozenset(conjunto_destino))
            
            if any(estado in self.estados_finais for estado in conjunto_origem):
                finais.add(origem)
        
        return AutomatoFinito(inicial, finais, self.alfabeto, transicoes)
    
    def pegar_estados_produtivos(self) -> FrozenSet[Estado]:
        """Retorna o conjunto de estados que alcançam pelo menos um estado de aceitação."""

        resultado: List[Estado] = []

        for origem in self.estados:
            alcancaveis = self.pegar_alcancaveis(origem)

            if any(estado in self.estados_finais for estado in alcancaveis):
                resultado.append(origem)
        
        return frozenset(resultado)

    def descartar_estados_inuteis(self) -> "AutomatoFinito":
        """
        Retorna o autômato finito equivalente que não possui
        estados inalcançáveis ou mortos.
        """

        alcancaveis = self.pegar_alcancaveis(self.estado_inicial)
        produtivos = self.pegar_estados_produtivos()

        inalcancaveis = self.estados - alcancaveis
        mortos = self.estados - produtivos

        descartados = set([*inalcancaveis, *mortos])

        transicoes: List[Transicao] = [
            transicao for transicao in self.transicoes()
            if transicao[0] not in descartados
            and transicao[2] not in descartados
        ]
        finais = self.estados_finais - descartados

        return AutomatoFinito(
            self.estado_inicial, finais, self.alfabeto, transicoes
        )

    def calcular_estados_equivalentes(self) -> FrozenSet[FrozenSet[Estado]]:
        """Calcula o conjunto de classes de equivalência do autômato."""

        # partição inicial de estados não-finais e finais
        classes = frozenset([
            self.estados - self.estados_finais,
            self.estados_finais
        ])
        visitados = set()

        while True:
            mapa_classes: Dict[Tuple, Set[Estado]] = {}

            for estado in self.estados:
                # lista de índices das classes que este estado vai
                # para cada símbolo do alfabeto.
                classes_destino: List[int] = []

                for simbolo in self.alfabeto:
                    destinos = self.transicao(estado, simbolo)

                    # -1 se o estado não possui transição por este símbolo
                    if not destinos:
                        classes_destino.append(-1)
                        continue
                    
                    destino, *_ = destinos

                    # procura a classe que possui este estado
                    for i, classe in enumerate(classes):
                        if destino not in classe:
                            continue
                        classes_destino.append(i)
                        break
                
                final = estado in self.estados_finais
                chave = (*classes_destino, final)

                # adiciona este estado a sua classe equivalente
                classe: Set[Estado] = mapa_classes.setdefault(chave, set())
                classe.add(estado)
            
            classes = frozenset(frozenset(classe) for classe in mapa_classes.values())

            if classes in visitados:
                return classes
            visitados.add(classes)
    
    def minimizar(self) -> "AutomatoFinito":
        """Retorna o autômato finito determinístico equivalente mínimo."""

        # descarta estados mortos e inalcançáveis
        automato = self.descartar_estados_inuteis()

        # calcula as classes de equivalencia
        estados_equivalentes = automato.calcular_estados_equivalentes()
        # une os estados equivalentes, considerando apenas o nome do
        # primeiro estado em ordem lexicográfica crescente
        estados_unidos = [sorted(classe)[0] for classe in estados_equivalentes]

        # cria um dicionário que mapeia os estados pelos
        # estados equivalentes as classes de equivalência
        mapa: Dict[Estado, Estado] = {}
        for estado_unido, classe in zip(estados_unidos, estados_equivalentes):
            for estado in classe:
                mapa[estado] = estado_unido
        
        # calcula as novas transições, estado inicial e estados finais
        transicoes: List[Transicao] = [
            [mapa[origem], simbolo, mapa[destino]]
            for origem, simbolo, destino in automato.transicoes()
        ]
        inicial = mapa[automato.estado_inicial]
        finais = set(mapa[estado] for estado in automato.estados_finais)

        return AutomatoFinito(inicial, finais, automato.alfabeto, transicoes)

    def serializar(self) -> str:
        """Retorna a representação em string do autômato."""

        num_estados = len(self.estados)
        inicial = self.estado_inicial
        finais = "{" + ",".join(sorted(self.estados_finais)) + "}"
        alfabeto = "{" + ",".join(sorted(self.alfabeto)) + "}"

        t = self.transicoes()
        t = sorted(t, key=lambda v: v[1])
        t = sorted(t, key=lambda v: v[0][1:-1] if v[0].startswith("{") else v[0])

        transicoes = ";".join(",".join(transicao) for transicao in t)

        return f"{num_estados};{inicial};{finais};{alfabeto};{transicoes}"


def parse(entrada: str) -> AutomatoFinito:
    """
    Retorna o autômato finito descrito pela entrada fornecida.

    Formato da entrada:
    <número de estados>;<estado inicial>;{<estados finais>};{<alfabeto>};<transições>

    Formato da transição:
    <estado origem>,<simbolo do alfabeto>,<estado destino>
    """

    # remove todos os espaços em branco
    entrada = re.sub(r"\s+", "", entrada)

    _, inicial, finais_str, alfabeto_str, *transicoes_str = entrada.split(";")

    finais = set(finais_str[1:-1].split(","))
    alfabeto = set(alfabeto_str[1:-1].split(","))
    transicoes = set(tuple(t.split(",")) for t in transicoes_str)

    return AutomatoFinito(inicial, finais, alfabeto, transicoes)
