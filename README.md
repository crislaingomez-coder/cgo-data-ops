<div align="center">

<img src="assets/cgo-data-light.png" alt="CGO Data" width="230">

# Commerce Ops Intelligence

### Diagnóstico automatizado de operações de e-commerce com Python

`Python` `Pandas` `Data Quality` `E-commerce` `Logística` `Automação de Relatórios`

</div>

> Case autoral da CGO Data, construído com dados 100% sintéticos. Não utiliza informações de empresas, clientes ou processos seletivos.

## Problema de negócio

Uma operação de e-commerce acompanha pedidos em diferentes canais, estados e transportadoras. Quando os indicadores ficam dispersos em planilhas, o time demora para descobrir onde estão atrasos, devoluções, cancelamentos e custos excessivos.

Este projeto automatiza esse diagnóstico. A pessoa analista informa um CSV e recebe um relatório executivo que responde:

> Qual parte da operação exige intervenção primeiro, por quê e qual ação deve ser tomada?

## Decisões apoiadas

- Qual transportadora apresenta maior risco combinado?
- Em qual canal os cancelamentos estão acima da meta?
- Que estado concentra mais chamados de atendimento?
- O custo de frete está proporcional à receita?
- O SLA está melhorando ou piorando ao longo dos dias?
- Quais ações devem ser tratadas como P1, P2 ou P3?

## O que a automação faz

1. Valida as 12 colunas obrigatórias.
2. Converte datas e campos numéricos.
3. Detecta e remove linhas duplicadas.
4. Bloqueia inconsistências, como entregas no prazo maiores que o total de pedidos.
5. Calcula oito indicadores operacionais.
6. Compara transportadoras, canais e estados.
7. Calcula um score de risco de 0 a 100.
8. Gera um plano de ação com evidência e responsável sugerido.
9. Produz um relatório HTML responsivo com a identidade CGO Data.

## Indicadores e metas demonstrativas

| Indicador | Meta usada no case |
|---|---:|
| SLA de entrega | ≥ 92% |
| Taxa de devolução | ≤ 8% |
| Taxa de cancelamento | ≤ 4% |
| Frete sobre receita | ≤ 12% |
| Chamados a cada 100 pedidos | ≤ 6 |

As metas são parâmetros demonstrativos do case e não representam políticas de uma empresa real.

## Dados analisados

O dataset simula sete dias de operação, com:

- três canais de venda;
- três transportadoras;
- quatro estados;
- pedidos, receita e custo de frete;
- prazo médio e entregas dentro do SLA;
- devoluções, cancelamentos e chamados.

O arquivo de exemplo está em [`data/example/operacao_ecommerce.csv`](data/example/operacao_ecommerce.csv).

## Como executar

```bash
python -m venv .venv
```

No Windows:

```bash
.venv\Scripts\activate
pip install -r requirements.txt
python src/analyze.py data/example/operacao_ecommerce.csv
```

O resultado será criado em:

```text
reports/commerce_ops_intelligence.html
```

Abra esse arquivo no navegador. Ele é independente e já contém a logo e a marca-d'água CGO Data.

## Estrutura do projeto

```text
cgo-data-ops/
├── assets/             # Identidade visual CGO Data
├── data/example/       # Dataset sintético para demonstração
├── reports/            # Relatórios gerados localmente
├── src/analyze.py      # Validação, análise e geração do relatório
├── requirements.txt
└── README.md
```

## Competências demonstradas

- Tradução de um problema operacional em indicadores.
- Limpeza e validação de dados com Pandas.
- Criação de regras de negócio explicáveis.
- Análise multidimensional.
- Priorização de ações por criticidade.
- Automação de relatórios executivos.
- Comunicação visual orientada à tomada de decisão.

## Próximas evoluções

- Testes automatizados para as regras de validação.
- Configuração externa das metas por YAML ou JSON.
- Exportação opcional para PDF.
- Histórico consolidado das execuções.
- Execução automática com GitHub Actions.

---

<div align="center">

**CGO Data — Dados que orientam decisões.**

</div>
