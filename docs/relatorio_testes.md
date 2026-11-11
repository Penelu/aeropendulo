# Relatório de testes — Aeropêndulo

Diário dos ensaios de bancada: o que foi feito, as medições e as decisões.
As seções numeradas são escritas à mão. As entradas em "Registros automáticos" são adicionadas pelo `app/teste_bancada.py` a cada execução.

## Como reproduzir os testes

Requisitos: Python 3 com `pyserial` e a Nucleo no USB.
O PC tem dois Pythons: 3.13 (`python`) e 3.14 (o do botão "Run" do VS Code). Os dois já têm o `pyserial`. Se aparecer `No module named 'serial'`, rode `<python usado> -m pip install pyserial`.
Rodar sem argumento (botão "Run") abre um menu para escolher o teste.

| Etapa | Comando | O que exige de você |
|---|---|---|
| Placa sozinha | `python app/teste_bancada.py placa` | nada |
| IMU em repouso | `python app/teste_bancada.py imu` | deixar a IMU parada |
| Eixos da IMU | `python app/teste_bancada.py eixos` | segurar a haste na vertical e inclinar para o lado do empuxo |
| Motor | `python app/teste_bancada.py motor` | haste deitada e presa; dizer onde a hélice começa a girar; medir a tensão da fonte |
| Sinal do motor | `python app/teste_bancada.py sinal` | haste encostada num apoio, inclinada de 10 a 20° |
| Botão B1 | `python app/teste_bancada.py botao` | apertar o B1 com a haste deitada e depois em pé |
| Empuxo | `python app/teste_bancada.py empuxo` | ventilador soprando para cima sobre a balança; digitar os gramas em cada degrau |

A porta é detectada sozinha; se preciso, use `--porta COM9`.

Teste manual alternativo: em qualquer terminal serial (Serial Monitor do VS Code, PuTTY), abra a COM9 a 115200 8N1, com fim de linha LF, e digite os comandos (`help`, `status`, `scan`, `imu`, `stop`...).

Para gravar o firmware sem toolchain, copie `aeropendulo.bin` para o drive `NODE_L476RG`.

---

## 1.0 — Placa sozinha (2026-11-07)

**Montagem:** Nucleo-L476RG só no USB, sem nenhum periférico.

**Compilação e gravação**
- Toolchain: GNU Arm 13.3.1, a que vem com o STM32CubeIDE 1.16.1 (`C:\ST\STM32CubeIDE_1.16.1\...\gnu-tools-for-stm32.13.3...\tools\bin`). Ela não está no PATH do sistema.
- Compilação do zero: **0 avisos**; flash 42 740 B (4,1 %) e RAM 6 712 B (6,8 %).
- Gravação por SWD com o STM32_Programmer_CLI 2.23 (`%LOCALAPPDATA%\stm32cube\bundles\programmer\2.23.0\bin`): verificação OK.
- ST-LINK VCP na **COM9**.

**Resultados**

| Teste | Observado | Esperado | |
|---|---|---|---|
| `help` / `status` | respondem; `IMU: NOT FOUND` | idem | OK |
| `scan` | nenhum dispositivo | nada no barramento | OK |
| `run` sem IMU | `IMU not found, cannot run` | recusar | OK |
| `motor 40` | duty 0,400, linhas `D` a cada 20 ms (50 Hz) | idem | OK |
| `stop` | `stopped` | idem | OK |
| `imu` sem IMU | envia linhas `I` zeradas | deveria recusar | **pendente** |

**Pendência:** o modo `imu` deveria recusar sem IMU, como o `run` faz. Assim um fio solto não pareceria um sensor "parado". A correção é pequena no `main.c` e aguarda aprovação.

## 1.1 — IMU no I2C (2026-11-07)

**Montagem:** IMU com VCC → 3V3, GND → GND, SDA → D14 (PB9), SCL → D15 (PB8). Módulo parado sobre a mesa.

**Resultados**

| Teste | Observado | Esperado | |
|---|---|---|---|
| `scan` | 0x68 | 0x68 ou 0x69 | OK |
| `status` | `IMU: MPU-9250 (WHO_AM_I 0x71) at 0x68, errors 0` | IMU encontrada | OK, mas o chip é outro (ver abaixo) |
| Módulo da gravidade (3 s, 61 amostras) | 0,982 g | 0,95 a 1,05 g | OK |
| Ruído do acelerômetro (desvio) | ≤ 0,003 g | < 0,01 g | OK |
| Bias do giroscópio após calibração | ≤ 0,04 °/s | < 0,5 °/s | OK |
| Ruído do giroscópio (desvio) | ≤ 0,10 °/s | < 0,3 °/s | OK |
| Deriva do `theta_gyro` em 3 s | 0,013° (desvio) | pequena | OK |

**Observações e decisões**
- **O sensor é um MPU-9250, não o ICM20600 (Grove IMU 9DOF) previsto.** O driver já aceita esse chip (mesmos registradores, ±4 g, ±500 °/s, DLPF de 41 Hz), então não é preciso mudar o firmware.
  - O magnetômetro AK8963 do MPU-9250 fica atrás do I2C interno do chip, por isso o 0x0C não aparece no `scan`. Isso não importa: o magnetômetro não é usado.
  - Falta atualizar o README e o `config.h`, que citam o Grove ICM20600.
- O `theta_acc` oscilou entre ±180° porque o módulo estava apoiado de lado (gravidade em −y). Com o mapeamento padrão (`up +x`, `side +y`), o ângulo fica perto de 180°, no ponto onde ele "dá a volta". Não é defeito: na montagem real, o ângulo fica entre 60° e 120°.
- Próximo passo: definir os eixos com o módulo na orientação de montagem (`teste_bancada.py eixos`).

## 1.2 — Motor ligado, preparação do firmware (2026-11-08)

**Montagem:**
- IMU soldada e ligada como na 1.1.
- Módulo do ventilador (L9110H) com INA e INB em **D10 e D11**, e VCC na bateria de **9 V**. A tensão da bateria em vazio foi medida com voltímetro: OK.
- Haste ainda deitada na mesa, sem a placa colada.

**Verificação antes de acionar o motor**
- IMU: `scan` → 0x68 e `status` → MPU-9250, 0 erros. Os pinos da IMU estão certos.
- O firmware gerava o PWM em D5 e D4, e o motor estava em D10 e D11, que ficavam sem configuração. O motor não responderia.
- Os comandos `motor` e `ramp` não respeitavam o `ulim`: o `ramp` chegaria a 100 % de 9 V num motor de 5 V.

**Decisões e mudanças no firmware**

| Mudança | Detalhe |
|---|---|
| PWM em D10 e D11 | A fiação foi mantida e o firmware adaptado. INA → D10 (PB6, TIM4_CH1) e INB → D11 (PA7, TIM3_CH2), 20 kHz. Nenhum timer atende os dois pinos, por isso são dois timers. O acesso fica em `board_fan_pwm()`. |
| Teto de PWM `dmax` | Limite aplicado em `motor_set_raw`, por onde passa toda saída: vale para `motor`, `ramp` e `run`. Padrão de 55 % (`DUTY_MAX_DEFAULT`), ≈ 5 V médios com 9 V. Com fonte de 5 V regulada, usar `dmax 100`. |
| `motor P` | Passa a mostrar o PWM aplicado depois do teto. |
| `imu` sem sensor | Agora recusa: "IMU not found" (pendência da 1.0, **resolvida**). |

- Compilação: **0 avisos**, flash 43 096 B. Gravado e verificado. `status` mostra `dmax 55%`.
- Regressão: `teste_bancada.py placa` e `imu` aprovados.
- O diagrama `docs/ligacoes.png` ainda mostra D5 e D4 e precisa ser refeito.

**Próximo ensaio:** `python app/teste_bancada.py motor`, com o usuário observando a hélice. O teste verifica:
- o PWM lido igual ao comando;
- os dois sentidos;
- a zona morta;
- o teto de 55 %;
- a tensão da bateria em carga.

## 1.3 — Teste do motor (2026-11-08)

**Montagem:** a da 1.2, com a bateria de 9 V e a haste deitada. Foram três execuções de `teste_bancada.py motor` (20:42, 20:43 e 20:45). Segundo o usuário, a última foi a mais confiável, e ela é a referência.

| Item | Resultado (execução de 20:45) | |
|---|---|---|
| PWM lido = comando, de 10 a 55 %, nos dois sentidos | igual em todos os degraus | OK |
| Gira nos dois sentidos | sim | OK |
| Zona morta (início do giro) | **frente ~25 %**, **ré ~20 %** (na 1ª execução: 20 % e 20 %) | medido |
| Teto `dmax` com `motor 80` | PWM em 55 % | OK |
| Tensão da bateria com o motor em 55 % | **5,9 V** (9 V em vazio) | **ruim** |
| Sentido do ar em `motor +` | "puxa o ar" (falta definir o lado) | pendente |

**Análise**
- **O caminho do PWM está validado:** pinos D10 e D11, dois timers, os dois sentidos e o teto.
- **Zona morta de 20 a 25 %, acima do padrão de 15 % do firmware.** A assimetria entre frente e ré é pequena. A medida é do início do giro (atrito estático); a velocidade em que o motor para ao descer deve ser menor.
- **A bateria de 9 V cai para 5,9 V em carga**, uma queda de 3,1 V, o que indica resistência interna alta (pilha quadrada fraca ou subdimensionada). Consequências:
  - em 55 %, o motor recebe só ~3,2 V médios, e não os 5 V previstos;
  - o empuxo vai cair à medida que a pilha descarrega, o que atrapalha a curva de empuxo e a sintonia do PID.
  - Para o controle, é preciso uma fonte firme: 12 V com step-down em 5 V, ou um carregador USB de 5 V / 2 A. Com ela, usar `dmax 100`.
- **O sentido do empuxo** será definido com a haste em pé e a IMU: `motor 40` deve aumentar θ; senão, `msign -1`.

**Decisões**
- Por ora, a alimentação do motor continua sendo a bateria de 9 V, com `dmax 55`. Em cada sessão, medir e anotar a tensão em vazio e em carga, para poder comparar os ensaios.
- A Nucleo **não** será alimentada pela mesma bateria (VIN): com a queda para 5,9 V em carga, o VIN fica abaixo dos 7 V mínimos e a placa reiniciaria. A Nucleo continua no USB, que também leva a serial.
- Próximo passo: colar a placa e a IMU na haste e rodar `teste_bancada.py eixos`.
- **Atualização:** a bateria foi trocada por uma **fonte de 5 V** (carregador USB com cabo cortado, D+ e D− isolados). Manter `dmax 55` até medir ≥ 4,5 V em carga no `teste_bancada.py motor`; depois, `dmax 100`.

## 1.4 — Remontagem com a fonte de 5 V (2026-11-08)

**Montagem:**
- Fonte de 5 V / 2 A (carregador USB com cabo cortado, D+ e D− isolados), medida em 5 V em vazio.
- IMU e placa coladas na haste.
- Nucleo pelo USB do PC.

**Problema: a IMU sumiu do I2C**
- `scan` vazio e `status` com `IMU: NOT FOUND`. O teste `teste_bancada.py imu` reprovou.
- Diagnóstico sem mexer na montagem, lendo os registradores do GPIOB pela SWD (`STM32_Programmer_CLI -c port=SWD mode=HOTPLUG -r32 0x48000410`):
  - Com os pull-ups internos, PB8 (SCL) e PB9 (SDA) ficam em nível alto: não há curto com o GND.
  - Com os **pull-downs** internos (PUPDR = 0x000A0100), as duas linhas continuaram em nível alto. Então existe um pull-up externo nos dois fios: o módulo estava alimentado e ligado a D14 e D15, mas mudo. Isso apontava para **SDA e SCL trocados**.
  - Os pull-ups internos foram restaurados depois (PUPDR = 0x00050100).
- **Causa confirmada:** SDA e SCL estavam invertidos na remontagem. Depois de desfazer a troca: `scan` → 0x68 e `status` → MPU-9250, 0 erros.

**Teste da IMU depois da correção:** reprovado em ruído, mas por **movimento da haste**, não por defeito.

| Item | Medido | Limite |
|---|---|---|
| Módulo da gravidade | 0,994 g (z para cima) | 0,95 a 1,05 g |
| Ruído do acelerômetro | 0,038 g | < 0,01 g |
| Ruído do giroscópio | 3,1 °/s, **só no eixo x**; y e z em 0,06 a 0,2 °/s | < 0,3 °/s |
| Bias do giroscópio | gx +1,21 °/s (a calibração foi feita com a haste se mexendo) | < 0,5 °/s |

- Na leitura por janelas de 1 s, o ruído de gx variou entre 0,6 e 3,5 °/s, com sinal lento (±3 °/s). Isso é oscilação mecânica em torno de x. Ruído elétrico apareceria nos três eixos.
- **Ação:** repetir `teste_bancada.py imu` com a haste apoiada estável e sem tocar nela. O teste espera o Enter antes de calibrar.

## 1.5 — IMU, motor a 5 V e eixos (2026-11-08)

**Resultados das execuções de 21:57 a 22:00**

| Teste | Resultado | |
|---|---|---|
| IMU em repouso | ruído do giroscópio 0,081 °/s, bias ≤ 0,01 °/s, ruído do acelerômetro 0,0017 g | OK |
| Motor a 5 V, PWM de 10 a 55 % | PWM lido = comando nos dois sentidos | OK |
| Zona morta a 5 V | **~30 %** nos dois sentidos | medido |
| Sentido do ar em `motor +` | "vai para a frente" | ver o `msign` com a haste em pé |
| Tensão da fonte em carga | não medida | pendente |
| Eixos | `axes +z -y +x`; a etapa 3 confirma: `theta_gyro` 135,4 = `theta_acc` 135,4 | OK |

- **Eixos:**
  - A reprovação do critério do giroscópio veio do script, não do sensor. Na etapa 2, a inclinação aconteceu fora da janela de 4 s (giro integrado ≈ 0°), e o script escolheu `+x` por um sinal de +1°.
  - A etapa 3 prova que `+x` está certo: com o sinal invertido, `theta_gyro` iria para ~55°.
  - A vertical em 95,4° é só a haste segurada fora do prumo.
- **Script `eixos` corrigido:**
  - o eixo do giroscópio passa a ser o perpendicular aos eixos UP e SIDE;
  - o sinal vem do movimento da etapa 2 ou, se não houver movimento, é corrigido na etapa 3;
  - o pedido agora diz "SÓ DEPOIS do Enter incline".
- **Script `motor` corrigido:** varre até o `dmax` atual, testa `motor 100` (carga máxima) e cobra **≥ 4,5 V** na fonte.

**Decisões e mudanças no firmware**
- `DUTY_MAX_DEFAULT` = **1,00** (fonte de 5 V regulada; com 9 V, usar `dmax 55`).
- Eixos padrão no `config.h`: UP = z (+), SIDE = y (−), GYRO = x (+).
- Compilação com **0 avisos**, gravada. `status`: `axes: up +z side -y gyro +x`, `dmax 100%`.
- Com `dmax 100`, a compensação da zona morta já leva u = 1 a 100 %, então a proposta de "compensação proporcional ao teto" deixa de ser necessária.
- Zona morta: o padrão de 15 % está abaixo dos ~30 % medidos. O valor final será definido com a balança (início do empuxo).

**Preocupação do usuário: o motor é fraco e a base é muito instável.** Não deve conseguir segurar 30° e precisa corrigir rápido desvios pequenos.
- Os 30° do firmware são só o **corte de segurança** (queda), não a faixa de operação.
- O ângulo máximo sustentável é dado por T_max · h_vent = m · g · d_CG · sen(φ). Precisamos medir:
  - **empuxo máximo** com a balança, nos dois sentidos;
  - **massa** da haste montada;
  - **altura do CG** e **altura do ventilador**.
- **Operar levemente inclinado:** com θ_ref ≈ 85° em vez de 90°, a gravidade puxa a haste contra o empuxo, e o ventilador fica **sempre girando para frente**, na faixa linear, sem cruzar a zona morta nem inverter. Inverter a hélice é lento: ela desacelera, cruza os ~30 % mortos e acelera no outro sentido. É o pior cenário para corrigir rápido. O lado certo (85° ou 95°) depende do `msign`.
- **Mecânica:**
  - peso embaixo (Nucleo e fios perto do pivô) e ventilador o mais alto possível;
  - isso baixa o CG, reduz o torque da gravidade e deixa a queda mais lenta, o que dá tempo ao controle.

## 1.6 — Botão B1 e alimentação da Nucleo pela fonte de 5 V (2026-11-08)

**Pedido do usuário:**
- alimentar a Nucleo pela mesma fonte de 5 V do motor;
- usar o botão azul para "segurar o ângulo atual": posicionar a haste, apertar, e o controle corrige as imperfeições.

**Firmware**
- **B1 (PC13):** entrada com pull-up, lida no laço de 5 ms com debounce de 50 ms (`BUTTON_DEBOUNCE_MS`). Age no aperto, não na soltura.

  | Estado | Aperto de B1 |
  |---|---|
  | parado (ou em `imu`, `motor` ou `ramp`) e θ entre 70° e 110° | `ref` = θ atual e liga o controle (`button: run: ref X`) |
  | parado e θ fora de 70° a 110° | recusa (`button: theta X outside 70..110, not started`) |
  | controlando | desliga tudo (`button: stopped`): **parada de emergência física** |

- O comando `run` e o botão usam a mesma função `start_run()`.
- Compilação com **0 avisos**, flash 43 552 B, gravada. Em repouso, PC13 = 1 (GPIOC IDR = 0x2000). O `aeropendulo.bin` da raiz foi atualizado.
- Teste: `python app/teste_bancada.py botao`.

**Alimentação da Nucleo pela fonte de 5 V (fiação, sem firmware)**
- +5 V da fonte → pino **E5V** (CN7, pino 6), com o **jumper JP5 em E5V**. **Não** usar o pino "5V", que é saída do regulador e briga com o USB.
- Os fios da Nucleo saem **direto dos bornes da fonte** (ligação em estrela), não depois do módulo do motor.
- Um capacitor eletrolítico de **470 a 1000 µF** no VCC/GND do módulo do motor segura os picos de corrente da partida.
- Com E5V, ligar primeiro a fonte e só depois o USB, para o ST-LINK enumerar.
- O USB pode continuar ligado, só para a serial e a telemetria.
- Ao energizar, a IMU calibra o giroscópio: **a haste tem que estar parada**, deitada.

## 1.7 — Preparação do primeiro ensaio de equilíbrio (2026-11-08)

**Decisões do usuário**
- A Nucleo continua alimentada **só pelo USB**, por enquanto.
- Massa e altura do CG ainda não serão medidas, porque o cabo USB pesa e atrapalha a medição.

**Preparação**
- Novo teste `teste_bancada.py sinal`: com a haste em pé e segura frouxa pela base, um pulso de `motor 50` por 0,6 s.
  - O giro integrado (taxa do giroscópio) precisa ser positivo, ou seja, `motor +` aumenta θ.
  - Se for negativo, o script envia `msign -1`, que vale até o reset.
  - **Obrigatório antes do primeiro `run`:** com o sinal invertido, a malha vira realimentação positiva.
- App do PC: o matplotlib estava quebrado no Python 3.13 (faltava o `packaging`) e ausente no 3.14. **Instalado nos dois.**

**Sequência do ensaio:** `motor` → `sinal` → `botao` → equilíbrio com `python app/aeropendulo_app.py`.
- Ganhos iniciais: PD (`pid 0.10 0 0.010`) e `dz 25`.
- Ordem do ajuste: KP → KD → KI.

**Cabo USB:** o peso e a rigidez do cabo agem como torque de perturbação.
- A parte constante é compensada pelo integrador; a parte variável vira ruído de perturbação.
- Para minimizar: prender o cabo na haste **perto da base** (braço de alavanca pequeno), com uma laçada frouxa, sem puxar.

## 1.8 — Motor até 100 % e primeiro acionamento pelo botão (2026-11-08)

| Item | Resultado | |
|---|---|---|
| PWM de 10 a 100 %, nos dois sentidos | lido = comando | OK |
| Zona morta a 5 V | ~30 % nos dois sentidos | medido |
| `motor 100` | PWM em 100 % | OK |
| **Tensão da fonte em carga máxima** | **4,85 V** (queda de 3 %; a bateria de 9 V caía 34 %) | OK (≥ 4,5 V) |
| Botão B1 com a haste em pé | o controle ligou (B1 OK), mas **empurrou a haste a favor da queda** | **sinal invertido** |

- **Correção:** a primeira descrição foi lida como "contra a queda", mas o usuário esclareceu que o ventilador **empurrava a haste para cair**. Isso é **realimentação positiva**.
  - Os eixos da IMU estão coerentes: o `theta_gyro` acompanha o `theta_acc` na 1.5.
  - Portanto o invertido é o sentido do motor em relação a θ.
- **Mudança:** novo `MOTOR_SIGN_DEFAULT (-1)` no `config.h` (antes era `+1` fixo no `motor.c`).
  - Compilação com 0 avisos, gravada; `status`: `msign -1`. O `aeropendulo.bin` foi atualizado.
- **Confirmação pendente:** `teste_bancada.py sinal` deve dar "sinal correto" com `msign -1`.
- **Teste `sinal` refeito:** o pulso de 0,6 s com a haste na mão media mais o tremor da mão do que o empuxo (observação do usuário).
  - Agora a haste fica **encostada num apoio**, inclinada de 10 a 20°, sem ninguém segurar.
  - O PWM sobe de 30 % a 100 % em degraus de 5 % a cada 0,4 s, e para quando θ muda min(8°, inclinação − 3°). Assim a haste nunca chega à vertical.
  - Se `motor +` só aperta a haste contra o apoio, o script tenta `motor −`.
  - O sinal vem da direção do movimento (≥ 5°). Se estiver errado, o script inverte o `msign` atual.
- O B1 foi testado direto, sem o `teste_bancada.py botao`, então não há registro automático.

## 1.9 — Aquecimento do módulo do motor (2026-11-08) — ENSAIOS SUSPENSOS

**Ocorrido:** depois de alguns empurrões leves do ventilador, o módulo (L9110H) e os **terminais do módulo** ficaram muito quentes, e o motor ficou fraco. O usuário desligou tudo.

**Hipóteses, da mais para a menos provável**
1. **Corrente acima da capacidade do L9110H.** O chip aguenta ~0,8 A contínuos (pico ~1,5 a 2 A) e tem limitação térmica interna. A perda de força com o chip quente é o sintoma típico dessa limitação.
2. **Inversões rápidas de sentido.** Primeiro o ensaio com `msign` invertido (o motor saturando enquanto a haste caía), depois a malha alternando o sentido. Inverter um motor girando ("plugging") puxa até ~2 vezes a corrente de rotor travado.
3. **Contato ruim nos terminais.** Borne frouxo, solda fria ou fio fino: a resistência de contato esquenta (I²R) mesmo com corrente moderada. Terminais quentes apontam para isso.
4. Perdas de chaveamento do L9110H a 20 kHz (driver lento): contribuição possível, a confirmar.

**Medidas antes de voltar a ligar**
- Deixar esfriar e inspecionar se há cheiro, plástico deformado, borne frouxo ou solda fria.
- Medir a **resistência do motor**, desligado do módulo: a corrente de rotor travado é ≈ 5 V / R.
- Medir a **corrente do motor**: multímetro em série na faixa de 10 A, com `motor 50` e `motor 100` por poucos segundos.

**Propostas (aguardando decisão)**
- **Sem inversão:** `ulim 0 1` com θ_ref levemente inclinado. O ventilador só gira para frente e a gravidade dá a força de retorno. Elimina o "plugging" e é só configuração, sem código.
- Reduzir o teto (`dmax`) conforme a corrente medida.
- Se a corrente contínua passar de ~0,8 A, **trocar o driver**: por exemplo TB6612FNG (1,2 A contínuos, 3,2 A de pico) ou DRV8871 (3,6 A de pico).

**Decisão (usuário):**
- Sem cheiro de queimado.
- Não dá para soltar o motor do módulo nem medir a corrente agora: a medição exige as duas mãos.
- O módulo esquenta mesmo girando num sentido só.
- Decidido: **tirar a inversão e limitar o teto em 90 %**.

**Mudanças no firmware (`config.h`)**

| Parâmetro | Antes | Agora | Motivo |
|---|---|---|---|
| `U_MIN_DEFAULT` | −1,0 | **0,0** | o ventilador só gira para frente: sem inversão e sem "plugging" |
| `I_MIN_DEFAULT` | −0,40 | **0,0** | com u ≥ 0, um I negativo só acumularia (windup) |
| `DUTY_MAX_DEFAULT` | 1,00 | **0,90** | reduz a corrente e o aquecimento do L9110H |
| `REF_DEFAULT_DEG` | 90 | **85** | sem inversão, a haste opera inclinada; a gravidade é a força de retorno |
| `DEADZONE_DEFAULT` | 0,15 | **0,25** | o motor começa a girar em ~30 % a 5 V |

- **Botão B1:** com `ulim` mínimo ≥ 0 e θ ≥ 90°, recusa ("lean the other way"). O ventilador só consegue empurrar θ para cima, então a haste tem que estar do lado θ < 90°.
- Compilação com 0 avisos, flash 43 688 B, gravada. O `aeropendulo.bin` foi atualizado.
- **Cuidado térmico:** ensaios curtos (≤ 20 a 30 s), com pausa e verificação do módulo pelo toque entre um e outro.

## 2.0 — Decisão: novo protótipo mais leve (2026-11-08)

**Motivo:** o conjunto atual está pesado demais para o empuxo do ventilador. Ele tem:
- haste de MDF;
- Nucleo presa na haste;
- muitos fios e cabo USB.

Isso aumenta o torque da gravidade (m·g·d_CG) e o momento de inércia. Junto com o L9110H esquentando, o ventilador não tem margem para corrigir os distúrbios.

**Novo protótipo (planejado pelo usuário)**
- Haste de **PLA**, só com a **IMU** e o **ventilador**.
- Nucleo, módulo do motor e fonte **fora da haste**, ligados por fios externos.
- Esse arranjo se aproxima do protótipo em PLA do relatório inicial e do artigo de anti-windup (m ≈ 0,145 kg, CG a 0,069 m, empuxo a 0,212 m, J ≈ 1,1e-3 kg·m²). Os ganhos padrão foram escalados desse modelo.

**Recomendações de projeto**
- **IMU perto do pivô**, e não no topo.
  - O giroscópio mede a mesma taxa em qualquer altura.
  - O acelerômetro, quanto mais alto, mais sente a aceleração tangencial (r·α) e a vibração do ventilador, que contaminam o `theta_acc`.
  - Perto do pivô, os fios da IMU também têm braço de alavanca pequeno.
- **Ventilador o mais alto possível**, preso rígido (vibração vira ruído na IMU).
- **Fios saindo pela altura do pivô e ao longo do eixo do pivô** (perpendicular ao plano de giro). Assim, quando a haste gira, o fio torce em vez de dobrar, e o torque que ele faz fica mínimo.
  - Usar fio fino e flexível (de silicone, 26 a 30 AWG).
- **I2C com fio longo:**
  - comprimento abaixo de ~50 cm;
  - SDA trançado com GND e SCL trançado com GND;
  - motor separado do I2C.
  - O contador `errors` do `status` mostra se há falhas; se houver, baixar o I2C para 50 kHz.
- **Fios do motor:** um par trançado mais grosso que os de sinal.
- **Módulo do motor na base:** fora da haste ele pode ganhar dissipador. É boa hora para trocar por um TB6612FNG ou DRV8871 se o L9110H continuar esquentando.
- **Medir antes de montar:** massa de cada peça, altura do CG e altura do ventilador.
- **Empuxo do ventilador na balança:** dá para medir agora, com o ventilador atual solto, sem a haste.

**Novo teste `teste_bancada.py empuxo`:** curva de empuxo com balança de cozinha, só com `motor +`.
- **Montagem:** ventilador soprando para cima sobre um copo ou caixa, com tara feita com o motor parado.
- **Checagem do sentido:** `motor 40` e a pergunta "o ar sai para cima?".
- **Degraus:** de 30 % até o `dmax`, de 10 em 10. O motor gira enquanto o usuário digita os gramas. Um temporizador desliga em **12 s** (proteção térmica), com pausa de 3 s entre degraus.
- **Resultado:** tabela em g e mN, empuxo crescente, início do empuxo (> 1 g), empuxo máximo e temperatura do módulo.
- Fluxo validado com placa simulada; ainda falta o ensaio real.
- **Atualização:** houve uma confusão sobre o sentido do ar. O usuário confirmou a montagem com o **ar para cima**, e o teste voltou à versão original (só ar para cima, leitura positiva).
- **Sentido de giro:** o usuário notou que, no sentido atual (`motor +` com `msign -1`), o ventilador empurra menos, e que no sentido oposto o empuxo é visivelmente maior (hélice assimétrica).
  - O teste passou a perguntar o sentido de giro: **invertido (`motor −`, padrão)** ou normal (`motor +`). Assim dá para medir os dois e escolher o mais forte.
  - Se o invertido vencer, o controle deve usá-lo: trocar o `MOTOR_SIGN_DEFAULT` para +1 e **virar o ventilador na haste**, para o jato forte empurrar θ para cima. Depois, confirmar com o teste `sinal`.

**Curva de empuxo (22:52), sentido invertido (`motor −`), fonte de 5 V, `dmax 90`**

| PWM | 40 % | 50 % | 60 % | 70 % | 80 % | 90 % |
|---|---|---|---|---|---|---|
| Empuxo | 0 g | 1 g | 2 g | 3 g | 7 g | **9 g (88 mN)** |

- O empuxo é **muito baixo**: 9 gf no máximo, e só passa de 1 g acima de ~50 a 60 %, embora a hélice comece a girar em ~30 %.
  - A balança tem resolução de 1 g, então a curva é grosseira.
  - O sentido normal (`motor +`) ainda não foi medido para comparação.
- **Causas possíveis do empuxo baixo:**
  - queda de tensão no L9110H (driver bipolar, ~1 V ou mais com corrente), que deixa o motor com ~4 V;
  - PWM de 20 kHz num driver lento, que perde rendimento e esquenta;
  - módulo já aquecido.
- **Viabilidade:** o ângulo máximo sustentável é dado por sen φ_max = T·h_vent / Σ(m_i·d_i), com T e m em gramas e alturas medidas a partir do pivô.
  - Exemplo: só um ventilador de 20 g no topo (haste sem massa) daria sen φ_max = 9/20, φ_max ≈ 27°. Cada grama de haste e de fios reduz isso.
  - O protótipo novo precisa ser **muito leve**, com o ventilador no topo e todo o resto perto do pivô.
- **Próximos passos propostos:**
  1. medir o sentido normal para comparar;
  2. pesar o módulo do ventilador e a IMU na mesma balança;
  3. testar se baixar a frequência de PWM (por exemplo, para 1 a 2 kHz) aumenta o empuxo e reduz o aquecimento do L9110H.

**Comparação dos sentidos (22:57, sentido normal `motor +`)**

| PWM | 30 % | 40 % | 50 % | 60 % | 70 % | 80 % | 90 % |
|---|---|---|---|---|---|---|---|
| Normal (`motor +`) | 0 g | 0 g | 1 g | 1 g | 1 g | 3 g | **4 g** |
| Invertido (`motor −`) | — | 0 g | 1 g | 2 g | 3 g | 7 g | **9 g** |

- **O sentido invertido dá mais que o dobro do empuxo** (9 g contra 4 g), o que confirma a observação do usuário: a hélice é assimétrica.
- **Decisão:** o controle passa a usar o sentido invertido. Para isso, `MOTOR_SIGN_DEFAULT` = +1 e o ventilador é virado na haste.
- **O módulo L9110H ficou quente demais de novo**, mesmo com degraus de no máximo 12 s e pausas. O L9110H é inviável para este motor.

**Recomendação: trocar o L9110H por um MOSFET**
- O controle agora **só gira num sentido** (`ulim 0 1`), então a ponte H não é mais necessária. Um **MOSFET canal N de nível lógico** no lado baixo resolve:
  - quase não esquenta (Rds(on) de dezenas de mΩ);
  - entrega praticamente os 5 V inteiros ao motor, contra ~1 V ou mais de queda no L9110H. Isso deve **aumentar o empuxo**.
  - custa poucos reais.
- **Ligação:**
  - fonte +5 V → motor (+) → motor (−) → dreno; fonte → GND;
  - **diodo de roda livre** (1N5819 ou 1N4007) em paralelo com o motor, catodo no +5 V;
  - gate ← D10 por um resistor de 100 Ω, com 10 kΩ do gate ao GND (mantém o motor desligado no reset);
  - GND comum com a Nucleo.
- **O sentido forte é escolhido pela polaridade dos fios do motor**, não mais pelo firmware.
- **MOSFETs adequados para gate de 3,3 V:**
  - AO3400 (SMD, carga de gate baixa, aceita 20 kHz);
  - módulo pronto com AOD4184 / D4184;
  - IRLZ44N ou IRLB8721 (TO-220). Com estes, baixar o PWM para ~1 a 4 kHz, porque a carga de gate é alta para o GPIO.
  - **Não** usar o módulo "IRF520": ele não conduz bem com 3,3 V no gate.
- Alternativa com ponte H, se a inversão voltar a ser necessária: TB6612FNG ou DRV8871.

**Firmware:** nenhuma mudança estrutural necessária. No protótipo novo, refazer:
- `imu` (fio longo);
- `eixos` (nova orientação);
- `sinal`;
- a sintonia.

---

## Registros automáticos

### 2026-11-07 12:49 — `teste_bancada.py placa` (COM9) — APROVADO

- OK — console responde: 14 linhas no help
- OK — status responde: IMU: MPU-9250 (WHO_AM_I 0x71) at 0x68, errors 0
- OK — telemetria D a 50 Hz: 101 linhas em 2 s (esperado ~100)

### 2026-11-07 12:49 — `teste_bancada.py imu` (COM9) — APROVADO

- OK — IMU no barramento I2C: 0x68
- OK — IMU inicializada: IMU: MPU-9250 (WHO_AM_I 0x71) at 0x68, errors 0
- OK — amostras a 20 Hz: 61 em 3 s (esperado ~60)
- OK — modulo da gravidade: |a| = 0.981 g (ax +0.005, ay -0.975, az -0.109)
- OK — ruido do acelerometro: desvio max 0.0044 g (limite 0,01)
- OK — bias do giroscopio apos cal: gx +0.00, gy +0.01, gz -0.02 dps (limite 0,5)
- OK — ruido do giroscopio: desvio max 0.074 dps (limite 0,3)
- OK — sem erros de leitura I2C: IMU: MPU-9250 (WHO_AM_I 0x71) at 0x68, errors 0

### 2026-11-07 12:52 — `teste_bancada.py placa` (COM9) — APROVADO

- OK — console responde: 14 linhas no help
- OK — status responde: IMU: MPU-9250 (WHO_AM_I 0x71) at 0x68, errors 0
- OK — telemetria D a 50 Hz: 102 linhas em 2 s (esperado ~100)

### 2026-11-07 12:53 — `teste_bancada.py imu` (COM9) — APROVADO

- OK — IMU no barramento I2C: 0x68
- OK — IMU inicializada: IMU: MPU-9250 (WHO_AM_I 0x71) at 0x68, errors 0
- OK — amostras a 20 Hz: 62 em 3 s (esperado ~60)
- OK — modulo da gravidade: |a| = 0.981 g (ax +0.005, ay -0.975, az -0.108)
- OK — ruido do acelerometro: desvio max 0.0019 g (limite 0,01)
- OK — bias do giroscopio apos cal: gx -0.01, gy -0.00, gz -0.01 dps (limite 0,5)
- OK — ruido do giroscopio: desvio max 0.073 dps (limite 0,3)
- OK — sem erros de leitura I2C: IMU: MPU-9250 (WHO_AM_I 0x71) at 0x68, errors 0

### 2026-11-08 20:37 — `teste_bancada.py placa` (COM9) — APROVADO

- OK — console responde: 15 linhas no help
- OK — status responde: IMU: MPU-9250 (WHO_AM_I 0x71) at 0x68, errors 0
- OK — telemetria D a 50 Hz: 102 linhas em 2 s (esperado ~100)

### 2026-11-08 20:37 — `teste_bancada.py imu` (COM9) — APROVADO

- OK — IMU no barramento I2C: 0x68
- OK — IMU inicializada: IMU: MPU-9250 (WHO_AM_I 0x71) at 0x68, errors 0
- OK — amostras a 20 Hz: 61 em 3 s (esperado ~60)
- OK — modulo da gravidade: |a| = 0.974 g (ax -0.173, ay -0.957, az +0.060)
- OK — ruido do acelerometro: desvio max 0.0027 g (limite 0,01)
- OK — bias do giroscopio apos cal: gx -0.00, gy -0.00, gz -0.01 dps (limite 0,5)
- OK — ruido do giroscopio: desvio max 0.071 dps (limite 0,3)
- OK — sem erros de leitura I2C: IMU: MPU-9250 (WHO_AM_I 0x71) at 0x68, errors 0

### 2026-11-08 20:42 — `teste_bancada.py motor` (COM9) — APROVADO

- OK — firmware com teto de PWM: dmax 55 % (precisa <= 55 com 9 V)
- OK — PWM lido = comando (frente): 10->10, 15->15, 20->20, 25->25, 30->30, 35->35, 40->40, 45->45, 50->50, 55->55
- OK — motor gira (frente): comecou em ~20 % (zona morta)
- OK — PWM lido = comando (re): 10->10, 15->15, 20->20, 25->25, 30->30, 35->35, 40->40, 45->45, 50->50, 55->55
- OK — motor gira (re): comecou em ~20 % (zona morta)
- OK — teto limita 'motor 80': PWM lido 55 % (esperado 55)
- OK — tensao da bateria em carga: nao medida
- OK — sentido do ar em 'motor +': nao informado

### 2026-11-08 20:43 — `teste_bancada.py motor` (COM9) — APROVADO

- OK — firmware com teto de PWM: dmax 55 % (precisa <= 55 com 9 V)
- OK — PWM lido = comando (frente): 10->10, 15->15, 20->20, 25->25, 30->30, 35->35, 40->40, 45->45, 50->50, 55->55
- OK — motor gira (frente): comecou em ~25 % (zona morta)
- OK — PWM lido = comando (re): 10->10, 15->15, 20->20, 25->25, 30->30, 35->35, 40->40, 45->45, 50->50, 55->55
- OK — motor gira (re): comecou em ~20 % (zona morta)
- OK — teto limita 'motor 80': PWM lido 55 % (esperado 55)
- OK — tensao da bateria em carga: 5.9 V
- OK — sentido do ar em 'motor +': nao informado

### 2026-11-08 20:45 — `teste_bancada.py motor` (COM9) — APROVADO

- OK — firmware com teto de PWM: dmax 55 % (precisa <= 55 com 9 V)
- OK — PWM lido = comando (frente): 10->10, 15->15, 20->20, 25->25, 30->30, 35->35, 40->40, 45->45, 50->50, 55->55
- OK — motor gira (frente): comecou em ~25 % (zona morta)
- OK — PWM lido = comando (re): 10->10, 15->15, 20->20, 25->25, 30->30, 35->35, 40->40, 45->45, 50->50, 55->55
- OK — motor gira (re): comecou em ~20 % (zona morta)
- OK — teto limita 'motor 80': PWM lido 55 % (esperado 55)
- OK — tensao da bateria em carga: 5.9 V
- OK — sentido do ar em 'motor +': puxa o ar

### 2026-11-08 21:51 — `teste_bancada.py placa` (COM9) — APROVADO

- OK — console responde: 15 linhas no help
- OK — status responde: IMU: NOT FOUND (WHO_AM_I 0x00) at 0x00, errors 0
- OK — telemetria D a 50 Hz: 102 linhas em 2 s (esperado ~100)

### 2026-11-08 21:51 — `teste_bancada.py imu` (COM9) — REPROVADO

- **FALHA** — IMU no barramento I2C: nada encontrado
- **FALHA** — IMU inicializada: IMU: NOT FOUND (WHO_AM_I 0x00) at 0x00, errors 0
- **FALHA** — amostras a 20 Hz: 0 em 3 s (esperado ~60)

### 2026-11-08 21:55 — `teste_bancada.py imu` (COM9) — REPROVADO

- OK — IMU no barramento I2C: 0x68
- OK — IMU inicializada: IMU: MPU-9250 (WHO_AM_I 0x71) at 0x68, errors 0
- OK — amostras a 20 Hz: 61 em 3 s (esperado ~60)
- OK — modulo da gravidade: |a| = 0.994 g (ax -0.024, ay +0.049, az +0.992)
- **FALHA** — ruido do acelerometro: desvio max 0.0384 g (limite 0,01)
- **FALHA** — bias do giroscopio apos cal: gx +1.21, gy +0.11, gz -0.51 dps (limite 0,5)
- **FALHA** — ruido do giroscopio: desvio max 3.144 dps (limite 0,3)
- OK — sem erros de leitura I2C: IMU: MPU-9250 (WHO_AM_I 0x71) at 0x68, errors 0

### 2026-11-08 21:57 — `teste_bancada.py imu` (COM9) — APROVADO

- OK — IMU no barramento I2C: 0x68
- OK — IMU inicializada: IMU: MPU-9250 (WHO_AM_I 0x71) at 0x68, errors 0
- OK — amostras a 20 Hz: 62 em 3 s (esperado ~60)
- OK — modulo da gravidade: |a| = 0.988 g (ax +0.608, ay -0.776, az +0.075)
- OK — ruido do acelerometro: desvio max 0.0017 g (limite 0,01)
- OK — bias do giroscopio apos cal: gx -0.01, gy +0.01, gz -0.01 dps (limite 0,5)
- OK — ruido do giroscopio: desvio max 0.081 dps (limite 0,3)
- OK — sem erros de leitura I2C: IMU: MPU-9250 (WHO_AM_I 0x71) at 0x68, errors 0

### 2026-11-08 21:59 — `teste_bancada.py motor` (COM9) — APROVADO

- OK — firmware com teto de PWM: dmax 55 % (precisa <= 55 com 9 V)
- OK — PWM lido = comando (frente): 10->10, 15->15, 20->20, 25->25, 30->30, 35->35, 40->40, 45->45, 50->50, 55->55
- OK — motor gira (frente): comecou em ~30 % (zona morta)
- OK — PWM lido = comando (re): 10->10, 15->15, 20->20, 25->25, 30->30, 35->35, 40->40, 45->45, 50->50, 55->55
- OK — motor gira (re): comecou em ~30 % (zona morta)
- OK — teto limita 'motor 80': PWM lido 55 % (esperado 55)
- OK — tensao da bateria em carga: nao medida
- OK — sentido do ar em 'motor +': vai para a frente

### 2026-11-08 22:00 — `teste_bancada.py eixos` (COM9) — REPROVADO

- OK — eixo vertical encontrado: +z = +0.987 g
- OK — inclinacao suficiente: y = +0.622 g (precisa > 0,25)
- **FALHA** — eixo do giroscopio encontrado: giro integrado x +1, y +0, z -0 graus
- **FALHA** — vertical = 90 graus: theta_acc = 95.4
- OK — inclinar para o empuxo aumenta theta: theta_acc = 135.4 (precisa > 105)
- OK — giroscopio coerente com acelerometro: theta_gyro 135.4 x theta_acc 135.4 (dif. < 5)
- OK — comando de eixos: axes +z -y +x

### 2026-11-08 22:19 — `teste_bancada.py motor` (COM9) — APROVADO

- OK — firmware com teto de PWM: dmax 100 %
- OK — PWM lido = comando (frente): 10->10, 15->15, 20->20, 25->25, 30->30, 35->35, 40->40, 45->45, 50->50, 55->55, 60->60, 65->65, 70->70, 75->75, 80->80, 85->85, 90->90, 95->95, 100->100
- OK — motor gira (frente): comecou em ~30 % (zona morta)
- OK — PWM lido = comando (re): 10->10, 15->15, 20->20, 25->25, 30->30, 35->35, 40->40, 45->45, 50->50, 55->55, 60->60, 65->65, 70->70, 75->75, 80->80, 85->85, 90->90, 95->95, 100->100
- OK — motor gira (re): comecou em ~30 % (zona morta)
- OK — teto respeitado em 'motor 100': PWM lido 100 % (esperado 100)
- OK — tensao da fonte em carga: 4.85 V (minimo 4,5 V)
- OK — sentido do ar em 'motor +': a haste empura para o lado oposto à queda. se caísse para a esquerda (-y) seria como se empurrasse para o oposto.

### 2026-11-08 22:24 — `teste_bancada.py sinal` (COM9) — REPROVADO

- OK — haste em pe no inicio: theta inicial 95.5
- **FALHA** — haste se mexeu com o pulso: giro -0.1 graus, theta 95.5 -> 95.8
- **FALHA** — 'motor +' aumenta theta: sinal INVERTIDO: enviei 'msign -1' (vale ate o reset)

### 2026-11-08 22:24 — `teste_bancada.py sinal` (COM9) — REPROVADO

- OK — haste em pe no inicio: theta inicial 93.4
- **FALHA** — haste se mexeu com o pulso: giro -0.1 graus, theta 93.4 -> 93.4
- **FALHA** — 'motor +' aumenta theta: sinal INVERTIDO: enviei 'msign -1' (vale ate o reset)

### 2026-11-08 22:24 — `teste_bancada.py sinal` (COM9) — REPROVADO

- OK — haste em pe no inicio: theta inicial 93.2
- **FALHA** — haste se mexeu com o pulso: giro -0.1 graus, theta 93.2 -> 93.2
- **FALHA** — 'motor +' aumenta theta: sinal INVERTIDO: enviei 'msign -1' (vale ate o reset)

### 2026-11-08 22:44 — `teste_bancada.py empuxo` (COM9) — REPROVADO

- **FALHA** — ar saindo para cima: vire o ventilador (ou confira o sentido) e rode de novo

### 2026-11-08 22:46 — `teste_bancada.py empuxo` (COM9) — REPROVADO

- **FALHA** — sentido do ar: resposta invalida; rode de novo

### 2026-11-08 22:48 — `teste_bancada.py empuxo` (COM9) — REPROVADO

- **FALHA** — ar saindo para cima: vire o ventilador (ou confira o sentido) e rode de novo

### 2026-11-08 22:52 — `teste_bancada.py empuxo` (COM9) — APROVADO

- OK — sentido de giro: invertido (motor -)
- OK — ar saindo para cima: o empuxo empurra o ventilador contra a balanca
- OK — empuxo cresce com o PWM: 40%=0g, 50%=1g, 60%=2g, 70%=3g, 80%=7g, 90%=9g
- OK — inicio do empuxo (> 1 g): 60 %
- OK — empuxo maximo medido: 9 g = 88 mN em 90 %, invertido (motor -)
- **FALHA** — temperatura do modulo aceitavel: não

### 2026-11-08 22:57 — `teste_bancada.py empuxo` (COM9) — APROVADO

- OK — sentido de giro: normal (motor +)
- OK — ar saindo para cima: o empuxo empurra o ventilador contra a balanca
- OK — empuxo cresce com o PWM: 30%=0g, 40%=0g, 50%=1g, 60%=1g, 70%=1g, 80%=3g, 90%=4g
- OK — inicio do empuxo (> 1 g): 80 %
- OK — empuxo maximo medido: 4 g = 39 mN em 90 %, normal (motor +)
- **FALHA** — temperatura do modulo aceitavel: não
