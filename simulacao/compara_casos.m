% COMPARA_CASOS  Script simulation of the three cases + sensitivity to Imax.
% Runs in MATLAB and GNU Octave (no toolboxes). Prints the tables and saves the
% figures used in the report to ./figuras.
%
%   (a) ideal actuator (no limits)          -> linear design reference
%   (b) measured actuator, no anti-windup   -> plain integrator
%   (c) measured actuator + limited integration (IL)

here = fileparts(mfilename('fullpath'));
if isempty(here), here = pwd; end
cd(here);
parametros_aeropendulo;
p.Tend = 5;
outdir = fullfile(here, 'figuras');
if ~exist(outdir, 'dir'), mkdir(outdir); end

cases = {struct('Fmin', -Inf,   'Fmax', Inf,    'Imin', -Inf,   'Imax', Inf), ...
         struct('Fmin', p.Fmin, 'Fmax', p.Fmax, 'Imin', -Inf,   'Imax', Inf), ...
         struct('Fmin', p.Fmin, 'Fmax', p.Fmax, 'Imin', p.Imin, 'Imax', p.Imax)};
names  = {'(a) sem saturação', '(b) saturação, sem AW', '(c) saturação + IL'};
colors = {[0.55 0.55 0.55], [0.80 0.15 0.15], [0.10 0.35 0.75]};

Fh = -p.m*p.g*p.h*sin((p.theta_r - 90)*pi/180) / p.L;
fprintf('Kp = %.3f N/rad, Ki = %.3f N/(rad.s), Kd = %.4f N.s/rad\n', p.Kp, p.Ki, p.Kd);
fprintf('Fmax = %.4f N, Fh(%.0f deg) = %.4f N, IL = [%.3f, %.4f] N\n', p.Fmax, p.theta_r, Fh, p.Imin, p.Imax);

% ---- metrics after the hand releases the rod
function m = metrics(o, p)
    after = o.t >= p.hold_t1;
    m.thmax = max(o.theta(after));
    m.Ipk = max(o.I);
    m.fell = o.fell;
    out_band = after & abs(o.theta - p.theta_r) > 1;
    last = find(out_band, 1, 'last');
    if o.fell || (~isempty(last) && last == numel(o.t))
        m.tr = Inf;
    elseif isempty(last)
        m.tr = 0;
    else
        m.tr = o.t(last) - p.hold_t1;
    end
    m.iae = sum(abs(o.theta(after) - p.theta_r)) * p.dt;
    m.err = mean(o.theta(end - round(0.2/p.dt):end)) - p.theta_r;   % last 0.2 s
end

res = cell(1, 3);
fprintf('\n%-24s %8s %8s %8s %8s %8s\n', 'Caso', 'thmax', 'Ipk(N)', 'tr(s)', 'IAE', 'tombou');
for i = 1:3
    res{i} = simula_aeropendulo(p, cases{i});
    m = metrics(res{i}, p);
    fprintf('%-24s %8.1f %8.3f %8.2f %8.1f %8d\n', names{i}, m.thmax, m.Ipk, m.tr, m.iae, m.fell);
end

% ---- figure 1: angle
f = figure('visible', 'off', 'position', [100 100 760 360]);
hold on; box on; grid on;
patch([p.hold_t0 p.hold_t1 p.hold_t1 p.hold_t0], [60 60 120 120], [0.92 0.92 0.92], 'EdgeColor', 'none');
for i = 1:3
    plot(res{i}.t, res{i}.theta, 'color', colors{i}, 'linewidth', 1.6);
end
plot([0 p.Tend], [p.theta_r p.theta_r], 'k:');
plot([0 p.Tend], [90 90], 'k-.');
plot([0 p.Tend], [66 66], 'k--', [0 p.Tend], [114 114], 'k--');
ylim([62 118]); xlim([0 p.Tend]);
xlabel('t (s)'); ylabel('\theta (graus)');
legend({'mão segurando', names{:}, 'referência', 'vertical', 'piso'}, 'location', 'eastoutside');
print(f, fullfile(outdir, 'fig_sim_angulo.png'), '-dpng', '-r200'); close(f);

% ---- figure 2: control signal and integral term
f = figure('visible', 'off', 'position', [100 100 760 460]);
subplot(2, 1, 1); hold on; box on; grid on;
for i = 2:3
    plot(res{i}.t, res{i}.u, 'color', colors{i}, 'linewidth', 1.4);
end
plot([0 p.Tend], [p.Fmax p.Fmax], 'k--', [0 p.Tend], [p.Fmin p.Fmin], 'k--');
ylim([-0.3 0.6]); xlim([0 p.Tend]); ylabel('u (N)');
legend({names{2:3}, 'limites do atuador'}, 'location', 'northeast');
subplot(2, 1, 2); hold on; box on; grid on;
for i = 2:3
    plot(res{i}.t, res{i}.I, 'color', colors{i}, 'linewidth', 1.4);
end
plot([0 p.Tend], [p.Imax p.Imax], 'k:', [0 p.Tend], [Fh Fh], 'k-.');
ylim([0 0.5]); xlim([0 p.Tend]); xlabel('t (s)'); ylabel('I (N)');
legend({names{2:3}, 'I_{max}', 'F_h'}, 'location', 'northeast');
print(f, fullfile(outdir, 'fig_sim_controle.png'), '-dpng', '-r200'); close(f);

% ---- sensitivity to the upper integrator bound
imax = [Inf p.Fmax p.Imax 0.055 0.030];
fprintf('\n%-10s %8s %8s %8s %8s\n', 'Imax(N)', 'thmax', 'tr(s)', 'erro', 'tombou');
f = figure('visible', 'off', 'position', [100 100 760 330]);
hold on; box on; grid on;
lbl = cell(1, numel(imax));
for j = 1:numel(imax)
    c = cases{3};  c.Imax = imax(j);
    o = simula_aeropendulo(p, c);
    m = metrics(o, p);
    fprintf('%-10.4f %8.1f %8.2f %8.2f %8d\n', imax(j), m.thmax, m.tr, m.err, m.fell);
    plot(o.t, o.theta, 'linewidth', 1.3);
    if isinf(imax(j)), lbl{j} = 'sem limite'; else, lbl{j} = sprintf('I_{max} = %.4f N', imax(j)); end
end
plot([0 p.Tend], [p.theta_r p.theta_r], 'k:');
ylim([62 118]); xlim([0 p.Tend]); xlabel('t (s)'); ylabel('\theta (graus)');
legend(lbl, 'location', 'eastoutside');
print(f, fullfile(outdir, 'fig_sim_sensibilidade.png'), '-dpng', '-r200'); close(f);

% ---- effect of how long the hand holds the rod
fprintf('\n%-10s %10s %10s %10s %10s\n', 'segura(s)', 'Ipk semAW', 'semAW', 'IL thmax', 'IL tr(s)');
for dur = [0.5 1.5 2.5]
    q = p;  q.hold_t1 = q.hold_t0 + dur;  q.Tend = q.hold_t1 + 3;
    ob = simula_aeropendulo(q, cases{2});  mb = metrics(ob, q);
    oc = simula_aeropendulo(q, cases{3});  mc = metrics(oc, q);
    st = 'ok'; if mb.fell, st = 'tomba'; end
    fprintf('%-10.1f %10.3f %10s %10.1f %10.2f\n', dur, mb.Ipk, st, mc.thmax, mc.tr);
end
fprintf('\nFiguras salvas em %s\n', outdir);
