# Simulação do aeropêndulo

Modelo não linear da haste, ventilador bidirecional com o empuxo medido (0,088 N no sentido forte, 0,039 N no reverso) e PID digital com integração limitada (*anti-windup*). Os parâmetros ficam todos em `parametros_aeropendulo.m`.

## No computador da UFBA (MATLAB + Simulink)

1. Copie a pasta `simulacao/` inteira e abra o MATLAB nela.
2. Rode `roda_simulink`.
   - Na primeira vez, o script cria o `aeropendulo.slx` pelo `cria_modelo_aeropendulo.m`.
   - Em seguida, roda os três casos: (a) sem saturação, (b) saturação sem *anti-windup*, (c) saturação com integração limitada.
   - Mostra o ângulo e o termo integral, e imprime a diferença para a simulação por script.
3. Para abrir o diagrama, digite `open_system('aeropendulo')`.

Resultado esperado: a diferença para o script fica em décimos de grau, e os casos batem com a Tabela 5 do relatório.
- (b) tomba em 114°.
- (c) chega a no máximo 89,2° e volta à referência.

> O `cria_modelo_aeropendulo.m` foi escrito sem acesso a uma licença do Simulink, porque a licença de rede da UFBA não estava disponível. Se algum parâmetro de bloco der erro, a mensagem do MATLAB indica o bloco. As equações estão no cabeçalho do script.

## Sem Simulink (MATLAB ou GNU Octave)

Rode `compara_casos`. O script usa só `simula_aeropendulo.m` (sem *toolboxes*), imprime as tabelas e salva as figuras do relatório em `figuras/`.

No Octave, para salvar as figuras, use o executável com interface gráfica:

```
octave-gui --no-gui --eval "graphics_toolkit qt; compara_casos"
```

## Arquivos

| Arquivo | Função |
|---|---|
| `parametros_aeropendulo.m` | parâmetros da haste (projeto em PLA), do atuador medido, ganhos e limites da integração limitada |
| `simula_aeropendulo.m` | simulação por script (Euler, 0,5 ms; controlador a cada 5 ms) |
| `compara_casos.m` | casos, sensibilidade a `Imax`, efeito do tempo em que a mão segura a haste; figuras |
| `cria_modelo_aeropendulo.m` | gera o `aeropendulo.slx` com blocos padrão |
| `roda_simulink.m` | roda o Simulink e compara com o script |
