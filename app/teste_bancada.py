"""Bench tests for the aeropendulo, one step at a time.

Usage:
    python app/teste_bancada.py placa      # board alone: console and telemetry
    python app/teste_bancada.py imu        # IMU found, at rest: gravity, gyro bias and noise
    python app/teste_bancada.py eixos      # guided: find the "axes U S G" for the real mounting
    python app/teste_bancada.py motor      # guided: PWM path, direction, dead zone, duty cap, supply sag
    python app/teste_bancada.py sinal      # guided: rod leaning on a support, slow ramp, 'motor +' must increase theta
    python app/teste_bancada.py botao     # guided: blue button B1 (hold current angle / stop)
    python app/teste_bancada.py empuxo     # guided: thrust curve on a kitchen scale, either spin direction
    python app/teste_bancada.py            # no argument: asks which test

Options: --porta COM9 (auto-detects the ST-LINK if omitted).
Every run prints [OK]/[FALHA] per check and appends a summary to docs/relatorio_testes.md.
"""
import argparse
import datetime
import math
import os
import statistics as st
import sys
import threading
import time

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    sys.exit(f"pyserial nao instalado neste Python. Rode:\n  \"{sys.executable}\" -m pip install pyserial")

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'docs', 'relatorio_testes.md')
I_PERIOD_S = 0.05            # "I" lines come at 20 Hz
AXIS = 'xyz'

results = []                 # (check name, passed, detail)


def check(name, passed, detail):
    results.append((name, passed, detail))
    print(f"  [{'OK' if passed else 'FALHA'}] {name}: {detail}")


def ask(text):
    """Wait for Enter (skipped when there is no keyboard, e.g. in automated runs)."""
    try:
        input(f"\n>>> {text} [Enter] ")
    except EOFError:
        print(f"\n>>> {text} (sem teclado, seguindo)")


def answer(text):
    """Ask a question and return the typed text ('' when there is no keyboard)."""
    try:
        return input(f"\n>>> {text} ").strip('﻿ \t').lower()
    except EOFError:
        print(f"\n>>> {text} (sem teclado)")
        return ''


def find_port():
    for p in list_ports.comports():
        if 'STLink' in (p.description or '') or 'STMicro' in (p.manufacturer or ''):
            return p.device
    sys.exit("ST-LINK nao encontrado: conecte a Nucleo ou use --porta COMx")


class Board:
    def __init__(self, port):
        self.s = serial.Serial(port, 115200, timeout=0.1)
        time.sleep(0.3)
        self.s.reset_input_buffer()

    def lines(self, seconds):
        out, t_end = [], time.time() + seconds
        while time.time() < t_end:
            line = self.s.readline().decode(errors='replace').strip()
            if line:
                out.append(line)
        return out

    def cmd(self, text, seconds=1.0, show=True):
        self.s.reset_input_buffer()
        self.s.write((text + '\n').encode())
        out = self.lines(seconds)
        if show:
            print(f"  > {text}")
            for line in out[:12]:
                print(f"    {line}")
            if len(out) > 12:
                print(f"    ... (+{len(out) - 12} linhas)")
        return out

    def imu_rows(self, seconds):
        """Stream 'imu' mode and return rows [ax ay az gx gy gz theta_acc theta_gyro theta]."""
        rows = []
        for line in self.cmd('imu', seconds, show=False):
            parts = line.split(',')
            if parts[0] == 'I' and len(parts) == 10 and parts[1] != 'ax':
                rows.append([float(x) for x in parts[1:]])
        self.cmd('stop', 0.3, show=False)
        return rows


def col(rows, i):
    return [r[i] for r in rows]


# ---------------------------------------------------------------- tests
def test_placa(b):
    print("\n== Placa: console e telemetria ==")
    out = b.cmd('help')
    check("console responde", any('commands' in l for l in out), f"{len(out)} linhas no help")

    out = b.cmd('status')
    check("status responde", any(l.startswith('IMU:') for l in out), out[0] if out else "sem resposta")

    out = b.cmd('motor 0', 2.0, show=False)   # 0 % duty: safe even with the fan connected
    b.cmd('stop', 0.3, show=False)
    n = sum(1 for l in out if l.startswith('D,'))
    check("telemetria D a 50 Hz", 85 <= n <= 105, f"{n} linhas em 2 s (esperado ~100)")


def test_imu(b):
    print("\n== IMU: deteccao e repouso ==")
    out = b.cmd('scan')
    found = [a for a in ('0x68', '0x69') if any(a in l for l in out if l.startswith('I2C scan'))]
    check("IMU no barramento I2C", bool(found), ', '.join(found) or "nada encontrado")

    out = b.cmd('status')
    imu_line = next((l for l in out if l.startswith('IMU:')), '')
    check("IMU inicializada", 'NOT FOUND' not in imu_line and imu_line != '', imu_line)

    ask("Deixe a IMU PARADA sobre a mesa (calibracao do giroscopio + 3 s de leitura)")
    b.cmd('cal', 3.0)
    rows = b.imu_rows(3.0)
    check("amostras a 20 Hz", 50 <= len(rows) <= 70, f"{len(rows)} em 3 s (esperado ~60)")
    if not rows:
        return

    acc = [st.mean(col(rows, i)) for i in range(3)]
    g = math.sqrt(sum(a * a for a in acc))
    check("modulo da gravidade", 0.95 <= g <= 1.05, f"|a| = {g:.3f} g (ax {acc[0]:+.3f}, ay {acc[1]:+.3f}, az {acc[2]:+.3f})")

    acc_std = max(st.pstdev(col(rows, i)) for i in range(3))
    check("ruido do acelerometro", acc_std < 0.01, f"desvio max {acc_std:.4f} g (limite 0,01)")

    bias = [st.mean(col(rows, i)) for i in range(3, 6)]
    check("bias do giroscopio apos cal", max(abs(x) for x in bias) < 0.5,
          f"gx {bias[0]:+.2f}, gy {bias[1]:+.2f}, gz {bias[2]:+.2f} dps (limite 0,5)")

    g_std = max(st.pstdev(col(rows, i)) for i in range(3, 6))
    check("ruido do giroscopio", g_std < 0.3, f"desvio max {g_std:.3f} dps (limite 0,3)")

    out = b.cmd('status', show=False)
    imu_line = next((l for l in out if l.startswith('IMU:')), '')
    check("sem erros de leitura I2C", imu_line.endswith('errors 0'), imu_line)


def test_eixos(b):
    print("\n== Eixos: mapeamento da IMU na haste ==")
    print("  Monte a IMU na haste (ou segure-a) na mesma orientacao da montagem final.")
    print("  'Lado do empuxo' = lado para onde o ventilador empurra a haste com 'motor +'.")
    print("  Se ainda nao souber, escolha um lado; depois corrigimos com 'msign -1'.")

    ask("1/3: segure a haste VERTICAL e parada por 2 s")
    rest = b.imu_rows(2.0)
    acc0 = [st.mean(col(rest, i)) for i in range(3)]
    up = max(range(3), key=lambda i: abs(acc0[i]))
    s_up = 1 if acc0[up] > 0 else -1
    check("eixo vertical encontrado", abs(acc0[up]) > 0.9, f"{'+-'[s_up < 0]}{AXIS[up]} = {acc0[up]:+.3f} g")

    ask("2/3: segure VERTICAL; SO DEPOIS do Enter incline devagar ~30 graus para o lado do empuxo e segure (4 s)")
    tilt = b.imu_rows(4.0)
    acc1 = [st.mean(col(tilt[-10:], i)) for i in range(3)]   # last 0.5 s, held still
    others = [i for i in range(3) if i != up]
    side = max(others, key=lambda i: abs(acc1[i]))
    s_side = -1 if acc1[side] > 0 else 1    # tilting towards +side makes the side reading negative
    check("inclinacao suficiente", abs(acc1[side]) > 0.25, f"{AXIS[side]} = {acc1[side]:+.3f} g (precisa > 0,25)")

    # the pivot axis is the one perpendicular to UP and SIDE; only its sign needs the motion
    gyro = 3 - up - side
    turn = sum(col(tilt, 3 + gyro)) * I_PERIOD_S                   # integrated rate, deg
    s_gyro = 1 if turn >= 0 else -1
    moved = abs(turn) > 10
    print(f"  giro integrado em {AXIS[gyro]}: {turn:+.0f} graus"
          + ("" if moved else " (pouco movimento: o sinal sera conferido na etapa 3)"))

    sgn = lambda s: '+' if s > 0 else '-'
    axes_cmd = f"axes {sgn(s_up)}{AXIS[up]} {sgn(s_side)}{AXIS[side]} {sgn(s_gyro)}{AXIS[gyro]}"
    print(f"\n  Comando encontrado: {axes_cmd}")
    b.cmd(axes_cmd)

    ask("3/3: com o novo mapeamento: VERTICAL por 2 s, depois incline para o lado do empuxo e segure")
    rows = b.imu_rows(5.0)
    th0 = st.mean(col(rows[:20], 6))
    th1 = st.mean(col(rows[-10:], 6))
    gy1 = st.mean(col(rows[-10:], 7))
    check("vertical = 90 graus", abs(th0 - 90) < 5, f"theta_acc = {th0:.1f}")
    check("inclinar para o empuxo aumenta theta", th1 > 105, f"theta_acc = {th1:.1f} (precisa > 105)")
    coherent = abs(gy1 - th1) < 5
    if not coherent and not moved and abs((2 * th0 - gy1) - th1) < 5:   # gyro went the other way
        s_gyro = -s_gyro
        axes_cmd = f"axes {sgn(s_up)}{AXIS[up]} {sgn(s_side)}{AXIS[side]} {sgn(s_gyro)}{AXIS[gyro]}"
        print(f"  sinal do giroscopio invertido -> {axes_cmd}")
        b.cmd(axes_cmd)
        coherent = True
    check("giroscopio coerente com acelerometro", coherent,
          f"theta_gyro {gy1:.1f} x theta_acc {th1:.1f} (dif. < 5)")
    print(f"\n  Se tudo OK, coloque em config.h: UP={up} ({sgn(s_up)}1), SIDE={side} ({sgn(s_side)}1), GYRO={gyro} ({sgn(s_gyro)}1)")
    results.append(("comando de eixos", True, axes_cmd))


def duty_read(lines):
    """Last duty (-1..1) reported in the D telemetry lines, or None."""
    d = [float(l.split(',')[6]) for l in lines if l.startswith('D,') and len(l.split(',')) == 9]
    return d[-1] if d else None


def sweep(b, sign, cap):
    """Duty steps of 5 % from 10 % up to the cap, 1.5 s each; returns [(command %, duty read %)]."""
    steps = []
    for p in range(10, cap + 1, 5):
        d = duty_read(b.cmd(f'motor {sign * p}', 1.5, show=False))
        steps.append((p, None if d is None else abs(d) * 100))
        print(f"  motor {sign * p:+d} %  -> PWM lido {'?' if d is None else f'{d * 100:+.0f}'} %")
    b.cmd('stop', 0.3, show=False)
    return steps


def ask_start(direction):
    a = answer(f"Em qual % a helice COMECOU a girar ({direction})? (numero; 'n' se nao girou)")
    if a.replace(',', '.').replace('.', '', 1).isdigit():
        check(f"motor gira ({direction})", True, f"comecou em ~{a} % (zona morta)")
    else:
        check(f"motor gira ({direction})", False, "nao girou" if a == 'n' else "sem resposta")


def test_motor(b):
    print("\n== Motor: PWM, sentido, zona morta e teto ==")
    print("  Antes de comecar, confira:")
    print("   - GND da fonte/modulo ligado ao GND da Nucleo (terra comum)")
    print("   - INA -> D10, INB -> D11; VCC do modulo -> fonte (+)")
    print("   - helice livre, dedos e fios longe; haste deitada e presa na mesa")
    ask("Tudo conferido? (Ctrl+C cancela)")

    out = b.cmd('status')
    cap = next((l.split('dmax')[1].strip(' %') for l in out if 'dmax' in l), None)
    check("firmware com teto de PWM", cap is not None, f"dmax {cap} %" if cap else "firmware antigo: grave o novo")
    if cap is None:
        return
    cap = int(float(cap))

    for sign, direction in ((+1, 'frente'), (-1, 're')):
        ask(f"Sentido {direction}: degraus de 10 a {cap} %, 1,5 s cada. Observe quando a helice comeca a girar")
        steps = sweep(b, sign, cap)
        check(f"PWM lido = comando ({direction})", all(d is not None and abs(d - p) < 1 for p, d in steps),
              ', '.join(f"{p}->{'?' if d is None else round(d)}" for p, d in steps))
        ask_start(direction)

    ask(f"Carga maxima: 'motor 100' por 5 s (PWM deve ficar em {cap} %). MECA a tensao da fonte agora")
    d = duty_read(b.cmd('motor 100', 5.0, show=False))
    b.cmd('stop', 0.3, show=False)
    check("teto respeitado em 'motor 100'", d is not None and abs(d * 100 - cap) < 1,
          f"PWM lido {'?' if d is None else round(d * 100)} % (esperado {cap})")
    v = answer(f"Tensao da fonte com o motor em {cap} % (V; Enter se nao mediu):")
    try:
        check("tensao da fonte em carga", float(v.replace(',', '.')) >= 4.5, f"{v} V (minimo 4,5 V)")
    except ValueError:
        results.append(("tensao da fonte em carga", True, "nao medida"))
    a = answer("Com 'motor +' (frente), para que lado o AR sai? (a haste e empurrada para o lado oposto)")
    results.append(("sentido do ar em 'motor +'", True, a or "nao informado"))


def ramp_until_moves(b, sign, th0, limit):
    """Raise the duty slowly (motor +P or -P); stop as soon as theta moves 'limit' deg.
    Returns (duty % that moved the rod or None, theta change)."""
    for p in range(30, 101, 5):                  # starts at the ~30 % dead zone
        lines = b.cmd(f'motor {sign * p}', 0.4, show=False)
        th = [float(l.split(',')[2]) for l in lines if l.startswith('D,') and len(l.split(',')) == 9]
        if th and abs(th[-1] - th0) > limit:
            b.cmd('stop', 0.3, show=False)
            print(f"  motor {sign * p:+d} %: theta {th0:.1f} -> {th[-1]:.1f}")
            return p, th[-1] - th0
    b.cmd('stop', 0.3, show=False)
    print(f"  motor {sign * 30:+d}..{sign * 100:+d} %: a haste nao saiu do apoio")
    return None, 0.0


def test_sinal(b):
    print("\n== Sinal do motor: 'motor +' deve AUMENTAR theta ==")
    print("  Ninguem segura a haste: ela fica ENCOSTADA num apoio (caixa, livro, parede),")
    print("  inclinada 10 a 20 graus, apoiada nos pes. Mao perto, sem tocar.")
    print("  O motor sobe devagar e para assim que a haste descola alguns graus do apoio.")
    b.cmd('stop', 0.3, show=False)
    out = b.cmd('status', show=False)
    msign = next((int(l.split('msign')[1].split()[0]) for l in out if 'msign' in l), 1)

    ask("Haste encostada no apoio e parada?")
    th0 = st.mean(col(b.imu_rows(1.0), 8))
    lean = abs(th0 - 90)
    check("haste inclinada no apoio", 8 <= lean <= 25, f"theta {th0:.1f} (precisa de 65..82 ou 98..115)")
    if not 8 <= lean <= 25:
        return
    limit = min(8.0, lean - 3)                   # always stops before the vertical

    p, d = ramp_until_moves(b, +1, th0, limit)
    if p is None:                                # 'motor +' pressed it against the support
        p, d = ramp_until_moves(b, -1, th0, limit)
        d = -d                                   # effect 'motor +' would have
    if p is None:
        check("motor descolou a haste", False, "nao descolou em nenhum sentido (apoio travando ou empuxo fraco)")
        return
    check("motor descolou a haste", True, f"com {p} % de PWM")
    ok = d > 0
    check(f"'motor +' aumenta theta (msign {msign:+d})", ok,
          "sinal correto" if ok else f"sinal INVERTIDO: enviei 'msign {-msign:+d}' (vale ate o reset)")
    if not ok:
        b.cmd(f'msign {-msign}', 0.3)


def run_and_ask(b, p, question, max_s=12.0):
    """Spin 'motor p' while the user answers; a timer stops the fan after max_s (heating)."""
    b.cmd(f'motor {p}', 0.3, show=False)
    timer = threading.Timer(max_s, lambda: b.s.write(b'stop\n'))
    timer.start()
    try:
        return answer(question)
    finally:
        timer.cancel()
        b.cmd('stop', 0.3, show=False)


def to_number(text):
    try:
        return float(text.replace(',', '.'))
    except ValueError:
        return None


def test_empuxo(b):
    print("\n== Empuxo do ventilador na balanca ==")
    print("  Monte o ventilador SOPRANDO PARA CIMA, em cima de um copo ou caixa (~10 cm)")
    print("  sobre a balanca, para a entrada de ar ficar longe do prato.")
    print("  O empuxo empurra o ventilador para baixo: a balanca mostra valor positivo.")
    print("  Fios soltos e sem puxar o ventilador. Ligue a balanca e faca a TARA com o motor parado.")
    b.cmd('stop', 0.3, show=False)
    out = b.cmd('status', show=False)
    cap = next((int(float(l.split('dmax')[1].strip(' %'))) for l in out if 'dmax' in l), 90)

    # propellers are asymmetric: run once in each spin direction and keep the stronger one
    way = answer("Sentido de giro: [i]nvertido ('motor -') ou [n]ormal ('motor +')? (Enter = i)")
    sign = 1 if way == 'n' else -1
    name = 'normal (motor +)' if sign > 0 else 'invertido (motor -)'
    results.append(("sentido de giro", True, name))

    ask("Ventilador montado e balanca tarada (0 g)?")
    up = run_and_ask(b, sign * 40, f"Com 'motor {sign * 40}' o ar esta saindo PARA CIMA? (s/n)")
    if up != 's':
        check("ar saindo para cima", False, "vire o ventilador e rode de novo")
        return
    check("ar saindo para cima", True, "o empuxo empurra o ventilador contra a balanca")

    print("\n  Em cada degrau o motor gira ate voce digitar a leitura (no maximo 12 s).")
    print("  Digite os gramas (ex.: 12,5); Enter vazio pula; 'x' encerra.")
    table = []
    for p in range(30, cap + 1, 10):
        time.sleep(3)                                   # short pause: lets the driver cool a bit
        a = run_and_ask(b, sign * p, f"motor {sign * p} %: leitura da balanca (g)?")
        if a == 'x':
            break
        g = to_number(a)
        if g is not None:
            table.append((p, g))
            print(f"    {p:3d} % -> {g:6.1f} g = {g * 9.81:6.1f} mN")

    if not table:
        check("leituras", False, "nenhuma leitura")
        return
    print("\n  PWM %   empuxo g   empuxo mN")
    for p, g in table:
        print(f"  {p:5d}   {g:8.1f}   {g * 9.81:9.1f}")
    rising = all(g2 >= g1 - 0.5 for (_, g1), (_, g2) in zip(table, table[1:]))
    check("empuxo cresce com o PWM", rising, ', '.join(f"{p}%={g:g}g" for p, g in table))
    start = next((p for p, g in table if g > 1.0), None)
    results.append(("inicio do empuxo (> 1 g)", True, f"{start} %" if start else "nao detectado"))
    p_max, g_max = table[-1]
    results.append(("empuxo maximo medido", True, f"{g_max:g} g = {g_max * 9.81:.0f} mN em {p_max} %, {name}"))
    hot = answer("O modulo do motor ficou quente demais para encostar o dedo por 3 s? (s/n)")
    check("temperatura do modulo aceitavel", hot != 's', "quente demais" if hot == 's' else "ok")


def wait_button(b, seconds=15):
    """Wait for the next 'button:' line from the board, or '' on timeout."""
    t_end = time.time() + seconds
    while time.time() < t_end:
        line = b.s.readline().decode(errors='replace').strip()
        if line.startswith('button:'):
            print(f"    {line}")
            return line
    return ''


def test_botao(b):
    print("\n== Botao azul B1: segurar o angulo atual / parar ==")
    b.cmd('stop', 0.3, show=False)

    ask("1/2: haste DEITADA (fora de 70..110 graus). Depois do Enter, aperte B1 uma vez")
    b.s.reset_input_buffer()
    line = wait_button(b)
    check("recusa fora da faixa", 'outside' in line, line or "nada recebido em 15 s")

    ask("2/2: SEGURE a haste em pe (perto da vertical). Depois do Enter, aperte B1, "
        "espere ~1 s SEGURANDO a haste e aperte B1 de novo")
    b.s.reset_input_buffer()
    line = wait_button(b)
    check("liga o controle no angulo atual", 'run: ref' in line, line or "nada recebido em 15 s")
    line = wait_button(b)
    check("segundo aperto para tudo", 'stopped' in line, line or "nada recebido em 15 s")
    b.cmd('stop', 0.3, show=False)


# ---------------------------------------------------------------- main
def log(test, port):
    ok = all(p for _, p, _ in results)
    stamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    lines = [f"\n### {stamp} — `teste_bancada.py {test}` ({port}) — {'APROVADO' if ok else 'REPROVADO'}\n"]
    lines += [f"- {'OK' if p else '**FALHA**'} — {n}: {d}" for n, p, d in results]
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    return ok


def main():
    tests = {'placa': test_placa, 'imu': test_imu, 'eixos': test_eixos, 'motor': test_motor, 'sinal': test_sinal,
             'botao': test_botao, 'empuxo': test_empuxo}
    ap = argparse.ArgumentParser(description="Testes de bancada do aeropendulo")
    ap.add_argument('teste', nargs='?', choices=tests)
    ap.add_argument('--porta')
    args = ap.parse_args()
    while args.teste not in tests:        # no argument (e.g. VS Code "Run"): ask
        try:
            args.teste = input(f"Qual teste? ({' / '.join(tests)}): ").strip('﻿ \t').lower()
        except EOFError:
            sys.exit("\nNenhum teste escolhido.")

    port = args.porta or find_port()
    print(f"Porta: {port}")
    b = Board(port)
    try:
        tests[args.teste](b)
    finally:
        b.cmd('stop', 0.3, show=False)   # always leave the motor off
    ok = log(args.teste, port)
    print(f"\nResultado: {'APROVADO' if ok else 'REPROVADO'} (registrado em docs/relatorio_testes.md)")
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
