# Qualidade e testes

O projeto possui validação automatizada no GitHub Actions para backend, banco e fluxo de navegador.

## Pipeline

A cada push ou pull request, o workflow executa duas etapas principais.

### Backend

A suíte Pytest é executada com:

- SQLite;
- PostgreSQL 16.

A suíte atual possui **22 testes**, cobrindo:

- cálculo de cobrança e casos de borda;
- validação e normalização de placas;
- autenticação;
- entrada e saída de veículos;
- idempotência da saída;
- prévia de valor desatualizada;
- estacionamento lotado;
- dados inválidos;
- restrições de integridade no banco;
- concorrência para a mesma vaga;
- histórico e exportação CSV;
- modo de demonstração.

### Frontend

O pipeline também executa:

- instalação das dependências;
- build de produção com Vite;
- teste E2E no Chromium com Playwright.

O fluxo de navegador cobre:

1. acesso ao modo de demonstração;
2. carga de dados fictícios;
3. registro de entrada;
4. rejeição de placa duplicada;
5. confirmação de saída;
6. consulta ao histórico;
7. exportação CSV;
8. renderização em desktop e mobile.

## Estado atual

O workflow configurado em `.github/workflows/ci.yml` está passando com:

| Verificação | Resultado |
| --- | --- |
| Pytest + SQLite | 22 testes aprovados |
| Pytest + PostgreSQL | 22 testes aprovados |
| Build Vite | aprovado |
| Playwright + Chromium | aprovado |

O badge de CI no README reflete o estado mais recente do workflow.

## Escopo da validação

Os testes automatizados verificam o comportamento esperado da aplicação, mas não substituem auditoria de segurança, teste de carga, homologação fiscal ou validação para operação comercial.
