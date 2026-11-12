# Projeto de Sistemas Distribuídos - Troca de Mensagens (ZeroMQ)

Este projeto implementa um sistema de troca de mensagens distribuído, contendo servidores, bots simulando clientes, um proxy (broker) para balanceamento e publicação (PUB/SUB e REQ/REP), além de um serviço de referência para coordenar a infraestrutura.

## Estratégia de Consistência e Replicação (Parte 5)

Para garantir que todos os servidores mantenham uma cópia consistente de todo o histórico de mensagens, foi implementada a estratégia de **Replicação Ativa Baseada em Eventos (Broadcast)** usando o padrão Publish-Subscribe.

### Como a replicação resolve o problema:
No modelo padrão, o Broker roteava as mensagens dos clientes para os servidores usando um balanceamento do tipo *Round-Robin*. Isso causava uma fragmentação no armazenamento: cada servidor detinha apenas as mensagens que ele próprio havia processado, ocasionando perda de dados irrecuperável caso um servidor falhasse. 
Com o modelo de replicação ativo, todo dado recebido e gravado por um servidor é imediatamente espelhado em todos os outros servidores da rede. Se qualquer servidor for interrompido, o histórico continuará íntegro nos sobreviventes, garantindo total tolerância a falhas.

### Como foi implementado:
Aproveitamos a infraestrutura de comunicação `PUB/SUB` do *ZeroMQ* que já estava provisionada no Broker (`proxy`) para a distribuição de mensagens aos clientes. 
1. Adicionou-se uma rotina secundária em **todas** as instâncias de servidor que efetua uma assinatura (Subscribe) contínua no tópico interno `REPLICA`.
2. Quando qualquer servidor recebe um comando de publicação do cliente, ele grava a mensagem no seu volume de disco local, mas imediatamente em seguida publica o pacote no canal `REPLICA` enviando junto o seu próprio identificador (ID do container).
3. Os demais servidores, ao detectarem um dado no tópico `REPLICA` cujo rementente é diferente de si mesmos, extraem a carga útil e persistem o dado em seus respectivos bancos (`mensagens.json`).
4. Para garantir a segurança dos dados simultâneos (corrida de threads na gravação do mesmo arquivo json), aplicou-se a biblioteca nativa `threading.Lock()` envolvendo as operações de I/O em disco.
