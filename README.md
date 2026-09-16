# Vaga Certa

[![CI](https://github.com/LucasSufredini/vaga-certa/actions/workflows/ci.yml/badge.svg)](https://github.com/LucasSufredini/vaga-certa/actions/workflows/ci.yml)
![React](https://img.shields.io/badge/React-19-20232a?logo=react)
![FastAPI](https://img.shields.io/badge/FastAPI-Python-009688?logo=fastapi)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql)
![Playwright](https://img.shields.io/badge/E2E-Playwright-2EAD33?logo=playwright)

Sistema full-stack para operação de estacionamentos, com controle de vagas, entrada e saída de veículos, cálculo de cobrança, histórico e exportação CSV.

O projeto combina regras de negócio, controle de concorrência no banco, idempotência na saída, valores monetários em centavos e testes automatizados com SQLite e PostgreSQL.

## Funcionalidades

- 24 vagas com seleção manual ou automática.
- Suporte a placas brasileiras antigas e Mercosul.
- Uma estadia ativa por placa e por vaga, garantida pelo banco.
- Prévia de cobrança antes da saída.
- Confirmação de saída idempotente.
- Histórico paginado com busca por placa.
- Exportação de movimentações em CSV.
- Painel responsivo para desktop e celular.
- Modo demonstração com dados fictícios.
- CI com backend, PostgreSQL, build do frontend e Playwright.

## Stack

| Camada | Tecnologias |
| --- | --- |
| Frontend | React 19, Vite, Lucide React |
| Backend | FastAPI, Pydantic, SQLAlchemy |
| Banco | SQLite local e PostgreSQL 16 |
| Testes | Pytest e Playwright |
| Infra | Docker, Docker Compose e GitHub Actions |

## Arquitetura

~~~mermaid
flowchart LR
    U[Operador] --> UI[React + Vite]
    UI -->|HTTP / JSON| API[FastAPI]
    API --> RULES[Regras de domínio]
    API --> ORM[SQLAlchemy]
    ORM --> DB[(SQLite / PostgreSQL)]
    CI[GitHub Actions] --> TESTS[Pytest + Playwright]
    TESTS --> API
    TESTS --> UI
~~~

A mesma aplicação FastAPI entrega a API e, no build final, os arquivos estáticos do frontend.

Mais detalhes em [docs/architecture.md](docs/architecture.md).

## Decisões técnicas

### Integridade no banco

Além das verificações na API, índices únicos parciais impedem duas estadias ativas com a mesma placa ou a mesma vaga. Isso protege a integridade mesmo quando requisições chegam quase simultaneamente.

### Saída idempotente

A confirmação só altera estadias ainda ativas. Repetir a solicitação depois de uma saída concluída devolve o registro existente, sem gerar outra movimentação.

### Dinheiro em centavos

Valores são armazenados como inteiros. R$ 12,00 é representado como 1200, evitando problemas de arredondamento com ponto flutuante.

### Tarifa preservada por estadia

A tarifa válida no momento da entrada é copiada para a estadia. Alterações futuras na tabela de preços não afetam registros já iniciados.

## Regra de cobrança

| Permanência | Valor |
| --- | ---: |
| Até 10 minutos, inclusive | R$ 0,00 |
| Mais de 10 minutos até 1 hora | R$ 12,00 |
| Cada hora adicional iniciada | + R$ 6,00 |

Exemplos:

- 10 minutos: R$ 0,00
- 11 minutos: R$ 12,00
- 60 minutos: R$ 12,00
- 60 minutos e 1 segundo: R$ 18,00
- 120 minutos: R$ 18,00

## Executar com Docker

Pré-requisito: Docker com Compose.

~~~sh
docker compose up --build
~~~

Abra:

~~~text
http://localhost:8000
~~~

Para encerrar:

~~~sh
docker compose down
~~~

## Executar sem Docker

Pré-requisitos:

- Python 3.12+
- Node.js 22+

Crie e ative o ambiente virtual:

~~~sh
python -m venv .venv
~~~

Windows PowerShell:

~~~powershell
.\.venv\Scripts\Activate.ps1
~~~

Linux/macOS:

~~~sh
source .venv/bin/activate
~~~

Instale as dependências e compile o frontend:

~~~sh
pip install -r backend/requirements.txt
cd frontend
npm install
npm run build
cd ../backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
~~~

Depois abra http://localhost:8000.

## Desenvolvimento do frontend

Com a API em execução na porta 8000:

~~~sh
cd frontend
npm install
npm run dev
~~~

O Vite encaminha as chamadas para `/api` ao backend local.

## Testes

Backend:

~~~sh
cd backend
python -m pytest tests -q
~~~

Frontend / E2E:

~~~sh
cd frontend
npm install
npm run build
npx playwright install chromium
npm run test:e2e
~~~

### Validação automatizada

| Verificação | Resultado |
| --- | --- |
| Pytest com SQLite | 22 testes aprovados |
| Pytest com PostgreSQL | 22 testes aprovados |
| Build Vite | aprovado |
| Playwright no Chromium | aprovado |

Detalhes em [docs/validation.md](docs/validation.md).

## Principais rotas da API

| Método | Rota | Função |
| --- | --- | --- |
| GET | /api/health | Saúde da aplicação e modo demo |
| GET | /api/overview | Indicadores, vagas e estadias ativas |
| POST | /api/stays | Registrar entrada |
| GET | /api/stays/{id}/quote | Calcular prévia ou consultar recibo |
| POST | /api/stays/{id}/checkout | Confirmar saída |
| GET | /api/history | Histórico paginado |
| GET | /api/history.csv | Exportar movimentações |
| POST | /api/demo | Popular banco vazio com dados fictícios |

A documentação interativa do FastAPI fica em http://localhost:8000/docs.

## Estrutura do projeto

~~~text
vaga-certa/
├── backend/
│   ├── app/
│   │   ├── domain.py
│   │   ├── main.py
│   │   └── models.py
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── main.jsx
│   │   └── style.css
│   └── tests/
├── docs/
│   ├── architecture.md
│   ├── demo-guide.md
│   └── validation.md
├── .github/workflows/ci.yml
├── Dockerfile
└── compose.yml
~~~

## Documentação

- [Arquitetura e decisões técnicas](docs/architecture.md)
- [Guia de uso](docs/demo-guide.md)
- [Qualidade e testes](docs/validation.md)

## Limitações conhecidas

Este é um projeto funcional de portfólio, não um sistema comercial pronto para produção.

Ainda não há:

- usuários, papéis e recuperação de senha;
- gateway de pagamento ou confirmação bancária;
- emissão fiscal;
- migrações versionadas;
- estorno com trilha de auditoria;
- backup e política de retenção;
- sensores, cancela ou leitura automática de placas.

## Próximas evoluções

1. Autenticação por usuário e perfis de acesso.
2. Alembic para migrações versionadas.
3. Auditoria de alterações e estornos.
4. Testes de carga e observabilidade.
5. Deploy público de demonstração.
6. Integração opcional com gateway de pagamento.

---

Projeto de portfólio com dados de demonstração fictícios.
