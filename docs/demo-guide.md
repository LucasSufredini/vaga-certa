# Guia de uso

Este documento apresenta um fluxo rápido para conhecer as principais funcionalidades do Vaga Certa.

## Iniciar a demonstração

Com a aplicação em execução, abra:

```text
http://localhost:8000
```

No modo de demonstração, selecione **Explorar demonstração**. Caso o banco esteja vazio, use **Carregar dados de exemplo** para preencher o painel com movimentações fictícias.

## Registrar uma entrada

1. Clique em **Registrar entrada**.
2. Informe uma placa válida, como `TES1T23`.
3. Opcionalmente, informe modelo e cor do veículo.
4. Escolha uma vaga livre ou deixe a seleção automática.
5. Confirme a entrada.

Após o registro, a vaga passa a aparecer como ocupada e o veículo é incluído na lista de estadias ativas.

O sistema impede:

- duas estadias ativas com a mesma placa;
- dois veículos ocupando a mesma vaga ao mesmo tempo;
- entrada quando não há vaga disponível.

## Registrar uma saída

Na lista de veículos no estacionamento:

1. Escolha **Registrar saída**.
2. Confira o tempo de permanência e a prévia do valor.
3. Selecione a forma de recebimento.
4. Confirme a saída.

Depois da confirmação:

- a estadia é encerrada;
- a vaga volta a ficar disponível;
- o registro aparece no histórico;
- repetir a mesma confirmação não cria uma nova movimentação.

## Consultar movimentações

Abra **Movimentações** para consultar estadias concluídas.

O histórico permite:

- busca por placa;
- paginação;
- visualização de entrada e saída;
- consulta do valor registrado;
- exportação em CSV.

## Tarifas

A regra atual é:

| Permanência | Valor |
| --- | ---: |
| Até 10 minutos | R$ 0,00 |
| Mais de 10 minutos até 1 hora | R$ 12,00 |
| Cada hora adicional iniciada | + R$ 6,00 |

A prévia pode mudar enquanto o veículo permanece estacionado. Por isso, a API recalcula o valor no momento da confirmação da saída.

## Observações

Os dados do modo demonstração são fictícios.

O sistema registra a forma de recebimento informada pelo operador, mas não processa Pix ou cartão, não realiza conciliação bancária e não emite documentos fiscais.
