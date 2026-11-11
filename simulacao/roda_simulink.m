% RODA_SIMULINK  Runs aeropendulo.slx for the three cases and compares it with
% the script simulation (simula_aeropendulo.m). MATLAB + Simulink (R2023b).
%
%   >> roda_simulink
%
% Creates the model on the first run (cria_modelo_aeropendulo.m).

here = fileparts(mfilename('fullpath'));
cd(here);
parametros_aeropendulo;
p.Tend = 5;
mdl = 'aeropendulo';
if ~exist(fullfile(here, [mdl '.slx']), 'file')
    cria_modelo_aeropendulo;
end
load_system(mdl);

cases = {struct('Fmin', -Inf,   'Fmax', Inf,    'Imin', -Inf,   'Imax', Inf), ...
         struct('Fmin', p.Fmin, 'Fmax', p.Fmax, 'Imin', -Inf,   'Imax', Inf), ...
         struct('Fmin', p.Fmin, 'Fmax', p.Fmax, 'Imin', p.Imin, 'Imax', p.Imax)};
names  = {'(a) sem saturação', '(b) saturação, sem AW', '(c) saturação + IL'};
colors = {[0.55 0.55 0.55], [0.80 0.15 0.15], [0.10 0.35 0.75]};

figure('Name', 'Aeropêndulo - Simulink', 'Position', [100 100 900 600]);
ax1 = subplot(2, 1, 1); hold on; grid on; box on;
patch([p.hold_t0 p.hold_t1 p.hold_t1 p.hold_t0], [60 60 120 120], [0.92 0.92 0.92], 'EdgeColor', 'none');
ax2 = subplot(2, 1, 2); hold on; grid on; box on;

fprintf('%-24s %10s %10s %16s\n', 'Caso', 'theta max', 'I pico', 'dif. script (graus)');
for i = 1:3
    c = cases{i};
    c.I0 = min(max(p.Fh, c.Imin), c.Imax);
    in = Simulink.SimulationInput(mdl);
    in = in.setVariable('p', p);
    in = in.setVariable('c', c);
    out = sim(in);

    t = out.theta.Time;  th = squeeze(out.theta.Data);
    tI = out.I.Time;     I = squeeze(out.I.Data);
    plot(ax1, t, th, 'Color', colors{i}, 'LineWidth', 1.5);
    if i > 1, plot(ax2, tI, I, 'Color', colors{i}, 'LineWidth', 1.4); end

    ref = simula_aeropendulo(p, c);                          % cross-check
    dif = max(abs(interp1(ref.t, ref.theta, t, 'linear', 'extrap') - th));
    fprintf('%-24s %10.1f %10.3f %16.2f\n', names{i}, max(th(t >= p.hold_t1)), max(I), dif);
end

plot(ax1, [0 p.Tend], [p.theta_r p.theta_r], 'k:', [0 p.Tend], [90 90], 'k-.', ...
     [0 p.Tend], [66 66], 'k--', [0 p.Tend], [114 114], 'k--');
ylim(ax1, [62 118]); ylabel(ax1, '\theta (graus)');
legend(ax1, ['mão segurando', names, {'referência', 'vertical', 'piso', ''}], 'Location', 'eastoutside');
plot(ax2, [0 p.Tend], [p.Imax p.Imax], 'k:', [0 p.Tend], [p.Fh p.Fh], 'k-.');
ylim(ax2, [0 0.5]); xlabel(ax2, 't (s)'); ylabel(ax2, 'I (N)');
legend(ax2, [names(2:3), {'I_{max}', 'F_h'}], 'Location', 'eastoutside');
