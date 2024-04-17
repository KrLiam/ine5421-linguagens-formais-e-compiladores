from automato import parse

def main():
    codificacao = input()

    if not codificacao:
        return

    afnd = parse(codificacao)
    afd = afnd.determinizar()
    codificacao_resultado = afd.serializar()

    print({codificacao_resultado})


if __name__ == "__main__":
    main()