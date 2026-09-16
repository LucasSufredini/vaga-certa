# Decisões de arquitetura

## Fluxo

A interface envia JSON por HTTP. FastAPI valida o corpo com Pydantic. SQLAlchemy
abre uma sessão por requisição. O banco persiste vagas e estadias. No build final,
a mesma aplicação entrega o HTML e os assets do React, eliminando a necessidade
de configurar CORS entre dois domínios.

## Modelo

Uma vaga tem várias estadias ao longo do tempo. Uma estadia contém placa, modelo,
entrada, saída, tarifa aplicada, valor final e forma de recebimento.
`exited_at IS NULL` significa que a estadia está ativa. Não existe um segundo
campo `ocupada` na vaga: isso evita duas fontes de verdade divergentes.

## Concorrência

Verificar a vaga livre apenas em Python não basta: duas requisições podem ler
"livre" simultaneamente. Os índices únicos parciais em `plate` e `spot_id`,
válidos apenas para estadias sem saída, protegem a regra no próprio banco.
Uma violação de unicidade causa rollback e HTTP 409.

A saída usa um UPDATE condicionado a `exited_at IS NULL`. Se duas requisições
competirem, somente uma efetiva a mudança. A outra retorna o registro existente.
O resultado fica persistido e a requisição pode ser repetida após uma falha de rede.
Não existe gateway externo, então não há transação distribuída de pagamento.

## Valores e tempo

Dinheiro é inteiro em centavos. A função de preço não depende de HTTP nem do banco,
o que permite testar bordas de 600, 601, 3600 e 3601 segundos com precisão.
O relógio da API é injetável nos testes. A persistência usa timestamps Unix;
os relatórios agrupam por dia em `America/Sao_Paulo`.

A tarifa é copiada para a estadia ao entrar. Isso conserva a regra contratada,
embora esta versão ainda não ofereça edição da tabela pela interface.

## API

| Método e rota | Papel |
|---|---|
| GET /api/health | Verificar disponibilidade e modo demo |
| GET /api/overview | Indicadores, vagas e estadias ativas |
| POST /api/stays | Registrar entrada |
| GET /api/stays/{id}/quote | Consultar prévia ou recibo existente |
| POST /api/stays/{id}/checkout | Confirmar saída uma única vez |
| GET /api/history | Histórico paginado e busca por placa |
| GET /api/history.csv | Exportar registros concluídos |
| POST /api/demo | Popular banco vazio com dados fictícios |

Além de health, todas as rotas de dados exigem `Authorization: Bearer <token>`.
O CSV exporta campos controlados e não inclui o campo livre de descrição do veículo,
evita fórmulas vindas desse campo. A serialização JSON e o React escapam o texto.

## Escolhas deliberadas e próximos passos

- Polling de 30 segundos: suficiente para demonstração; WebSocket adicionaria
  complexidade sem uma necessidade medida.
- SQLite local: fácil para quem vai clonar o projeto. PostgreSQL no Compose e CI:
  caminho para testar um banco de servidor.
- Token de operador: controle simples; não é apresentado como autenticação
  empresarial. Próximo passo seria usuários, sessões e trilha de auditoria.
- Histórico paginado, indicadores com consultas diretas: para alto volume,
  medir planos de execução e adicionar índices por datas antes de otimizar.
- Frontend concentrado em poucos arquivos: fácil de percorrer nesta primeira
  versão; separar hooks e componentes de telas ao adicionar novos módulos.

Referências técnicas consultadas:
[FastAPI — testes](https://fastapi.tiangolo.com/tutorial/testing/) e
[SQLAlchemy — consultas](https://docs.sqlalchemy.org/en/20/orm/queryguide/select.html).
