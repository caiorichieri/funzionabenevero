# Revisão geral do fluxo Pagamento → Fattura

## Contexto do problema

Um pagamento real foi feito (Silvia Drigo, 21/09/2026, Dr. Laura De Clara). Sintomas observados:

- O pagamento aparece corretamente em **Admin → Pagamenti** com status "In attesa" e o botão "Rimborsa" ativo.
- Em **Admin → Fatture** aparece o banner vermelho "1 pagamento senza fattura" com o nome do paciente e a data.
- A lista de fatture mostra "Nessuna fattura da mostrare" e "Totale Sanitarie € 0,00".
- O paciente recebeu o e-mail de confirmação do agendamento, mas **não recebeu a fattura**.
- O paciente logado **não vê a fattura** no próprio dashboard.

Conclusão: o pipeline fiscal pós-pagamento **falhou silenciosamente** entre o webhook de pagamento confirmado e a criação/entrega da fattura sanitaria.

## Papel do Stripe neste sistema (para alinhar entendimento)

Stripe é **apenas o processador de pagamento**. Ele não gera nem emite nenhuma fattura. O papel dele termina quando o cartão é cobrado com sucesso e ele envia um webhook `checkout.session.completed` ao nosso backend.

A partir desse ponto, **tudo é responsabilidade do nosso sistema**:

1. Registrar a transação como paga.
2. Criar o registro da Fattura Sanitaria (numeração FZ-AAAA-N sequencial).
3. Gerar o XML FatturaPA TD01 conforme normativa italiana.
4. Gerar o PDF humano-legível da fattura.
5. Fazer upload de XML e PDF ao Object Storage.
6. Enviar e-mail ao paciente com o PDF anexado.
7. Tornar a fattura visível no dashboard do paciente e no admin.

Se qualquer um destes passos falhar, o pagamento fica "órfão" — foi cobrado, mas sem fattura entregue. Foi exatamente o que aconteceu.

## Objetivo desta revisão

Deixar o fluxo Pagamento → Fattura **robusto, auto-recuperável e observável**, de forma que:

- Um erro num passo intermediário **não descarte** o trabalho: o pagamento continua marcado como pago e a fattura pode ser retomada.
- Falhas parciais fiquem **visíveis ao admin** com o erro exato, sem depender de ler logs.
- O admin possa **forçar a reemissão** de qualquer fattura pendente com um clique.
- O caso concreto da Silvia Drigo seja resolvido e a fattura chegue ao paciente.

## Escopo do trabalho (o que vai ser feito)

### 1. Recuperar o pagamento da Silvia Drigo (ação imediata)
Gerar manualmente a fattura em falta para o pagamento já cobrado, com XML + PDF, e enviar o e-mail ao paciente. Isso desbloqueia o caso real antes mesmo da correção estrutural.

### 2. Tornar o pipeline pós-pagamento resiliente
Reorganizar o handler do webhook de pagamento confirmado para:

- **Sempre** marcar a transação como paga primeiro (nunca perder essa informação).
- Executar geração de fattura, XML, PDF, upload e envio de e-mail em **passos independentes**, cada um com seu try/except.
- Ao falhar num passo, gravar no registro do pagamento (ou da fattura) o **erro exato** e o passo que falhou, para o admin ver.
- **Nunca** retornar erro ao Stripe (o Stripe fez a parte dele; retornar erro faz Stripe reentregar o webhook e duplicar tudo).
- Ser **idempotente**: se o mesmo webhook chegar duas vezes, não duplica fattura.

### 3. Auto-tentativa em segundo plano
Criar uma rotina que, periodicamente (ex.: a cada poucos minutos) e no boot do servidor, procura pagamentos pagos sem fattura completa e tenta terminar o processo automaticamente. Assim, uma falha transitória (Object Storage lento, Resend fora do ar) se auto-cura sem intervenção do admin.

### 4. Melhorar a diagnóstica no admin
No painel **Fatture**, o banner "pagamenti senza fattura" passa a mostrar, para cada caso:

- Em que passo travou (criação / XML / PDF / upload / e-mail).
- A mensagem de erro exata da última tentativa.
- Botão "Riprova" por linha (além do botão global "Genera N fatture mancanti").
- Botão "Reinvia e-mail" para casos em que a fattura existe mas o e-mail nunca saiu.

### 5. Garantir visibilidade da fattura ao paciente
Confirmar que assim que a fattura entra no estado "emessa", ela aparece imediatamente no dashboard do paciente, sem depender do e-mail ter sido enviado. O e-mail é entrega; o dashboard é fonte de verdade.

### 6. Validação
Testar o fluxo completo ponta-a-ponta (pagamento simulado → fattura → PDF → e-mail → dashboard) e simular falhas em cada passo para confirmar que o sistema se recupera.

## Fora de escopo (não será feito agora)

- Envio automático ao **SDI (Sistema di Interscambio)** da Fatture in Cloud / Aruba — continua manual, como já estava planejado no backlog.
- Coach Sessuale AI (Fase 19).
- Storico Sessioni no dashboard.
- E-mail 24h pós-sessão.
- Web Push (VAPID).
- Refatoração de `subprocess.run` no backup_service.
- Limpeza de dependências de hooks React.

Todos permanecem no backlog e voltam depois da estabilização do fluxo fiscal.

## Decisões que carregam risco fiscal / de UX

Assumindo os defaults abaixo salvo objeção:

1. **Numeração da fattura**: se a criação da fattura foi iniciada mas falhou depois (ex.: PDF), o número **é preservado** e a fattura fica em estado "em recuperação", nunca "descartada". Isso evita buracos na sequência fiscal.
2. **Retentativas**: até 5 tentativas automáticas em segundo plano com backoff. Depois disso, fica só à espera de retry manual do admin.
3. **E-mail ao paciente**: se falhar, a fattura permanece "emessa" (é o que importa para o fisco). O envio de e-mail é retentado separadamente e o admin pode reenviar manualmente. O paciente sempre consegue baixar do próprio dashboard.
4. **Idempotência**: usaremos o `payment_intent` do Stripe como chave única para nunca gerar duas fatture para o mesmo pagamento, mesmo com webhooks duplicados.

## Perguntas em aberto

Nenhuma que bloqueie o início. Se preferir mudar algum dos 4 defaults acima, é só sinalizar.
