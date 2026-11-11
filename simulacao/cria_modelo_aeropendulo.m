function cria_modelo_aeropendulo()
% CRIA_MODELO_AEROPENDULO  Builds aeropendulo.slx with standard Simulink blocks.
%
% Same equations as simula_aeropendulo.m (SI units, phi = theta - 90 deg):
%   rod      J*phi'' = m*g*h*sin(phi) - b*phi' + L*F + tau_d,  |phi| <= phi_bat
%   fan      tau_m*F' = sat(u, c.Fmin, c.Fmax) - F
%   PID      discrete (Ts), D on the measured rate (gyro), integrator with limited
%            state [c.Imin, c.Imax] = limited integration (Imin=-inf, Imax=inf: no AW)
%   tau_d    touch pulse + hand holding the rod (spring-damper) between hold_t0 and hold_t1
%
% Block parameters read the structs p (parametros_aeropendulo.m) and c (case),
% passed by roda_simulink.m with Simulink.SimulationInput.

mdl = 'aeropendulo';
if bdIsLoaded(mdl), close_system(mdl, 0); end
here = fileparts(mfilename('fullpath'));
if exist(fullfile(here, [mdl '.slx']), 'file'), delete(fullfile(here, [mdl '.slx'])); end
new_system(mdl);
set_param(mdl, 'SolverType', 'Fixed-step', 'Solver', 'ode4', 'FixedStep', 'p.dt', ...
          'StopTime', 'p.Tend');

    function b = blk(lib, name, pos, varargin)
        b = [mdl '/' name];
        add_block(lib, b, 'Position', pos, varargin{:});
    end
    function wire(src, dst)
        add_line(mdl, src, dst, 'autorouting', 'on');
    end

S = 'simulink/';
% ---------------------------------------------------------------- reference
blk([S 'Sources/Constant'], 'phi_r', [30 40 110 70], 'Value', 'p.phi_r');

% ---------------------------------------------------------------- controller (Ts)
blk([S 'Discrete/Zero-Order Hold'], 'ZOH phi', [150 120 190 150], 'SampleTime', 'p.Ts');
blk([S 'Discrete/Zero-Order Hold'], 'ZOH rate', [150 200 190 230], 'SampleTime', 'p.Ts');
blk([S 'Math Operations/Sum'], 'erro', [230 45 250 65], 'Inputs', '+-');
blk([S 'Math Operations/Gain'], 'Kp', [300 10 350 40], 'Gain', 'p.Kp');
blk([S 'Math Operations/Gain'], 'Ki', [300 70 350 100], 'Gain', 'p.Ki');
blk([S 'Discrete/Discrete-Time Integrator'], 'Integracao limitada', [380 65 450 105], ...
    'IntegratorMethod', 'Integration: Backward Euler', 'gainval', '1', ...
    'InitialCondition', 'c.I0', 'LimitOutput', 'on', ...
    'UpperSaturationLimit', 'c.Imax', 'LowerSaturationLimit', 'c.Imin', 'SampleTime', 'p.Ts');
blk([S 'Math Operations/Gain'], 'Kd (giroscopio)', [300 200 350 230], 'Gain', 'p.Kd');
blk([S 'Math Operations/Sum'], 'u = P + I - D', [490 40 510 120], 'Inputs', '++-');

% ---------------------------------------------------------------- actuator
blk([S 'Discontinuities/Saturation'], 'Limites do atuador', [550 65 600 95], ...
    'UpperLimit', 'c.Fmax', 'LowerLimit', 'c.Fmin');
blk([S 'Math Operations/Sum'], 'us - F', [640 70 660 90], 'Inputs', '+-');
blk([S 'Math Operations/Gain'], 'inv tau_m', [690 65 740 95], 'Gain', '1/p.tau_m');
blk([S 'Continuous/Integrator'], 'F', [770 65 810 95], 'InitialCondition', 'p.Fh');

% ---------------------------------------------------------------- rod
blk([S 'Math Operations/Gain'], 'L', [850 65 890 95], 'Gain', 'p.L');
blk([S 'Math Operations/Trigonometric Function'], 'sin', [850 130 890 160], 'Operator', 'sin');
blk([S 'Math Operations/Gain'], 'm g h', [910 130 960 160], 'Gain', 'p.m*p.g*p.h');
blk([S 'Math Operations/Gain'], 'b', [910 190 960 220], 'Gain', 'p.b');
blk([S 'Math Operations/Sum'], 'torques', [1000 60 1020 230], 'Inputs', '+++-');
blk([S 'Math Operations/Gain'], 'inv J', [1050 130 1090 160], 'Gain', '1/p.J');
blk([S 'Continuous/Integrator'], 'rate', [1120 130 1160 160], 'InitialCondition', '0', ...
    'ExternalReset', 'level');
blk([S 'Continuous/Integrator'], 'phi', [1200 130 1240 160], 'InitialCondition', 'p.phi_r', ...
    'LimitOutput', 'on', 'UpperSaturationLimit', 'p.phi_bat', ...
    'LowerSaturationLimit', '-p.phi_bat', 'ShowSaturationPort', 'on');

% ---------------------------------------------------------------- disturbances
blk([S 'Sources/Step'], 'toque inicio', [700 300 730 330], 'Time', 'p.td_t0', 'After', 'p.td_amp');
blk([S 'Sources/Step'], 'toque fim', [700 350 730 380], 'Time', 'p.td_t0 + p.td_dur', ...
    'After', '-p.td_amp');
blk([S 'Sources/Step'], 'mao pega', [700 420 730 450], 'Time', 'p.hold_t0', 'After', '1');
blk([S 'Sources/Step'], 'mao solta', [700 470 730 500], 'Time', 'p.hold_t1', 'After', '-1');
blk([S 'Math Operations/Sum'], 'janela mao', [770 440 790 480], 'Inputs', '++');
blk([S 'Sources/Constant'], 'phi mao', [700 540 780 570], 'Value', '(p.hold_theta - 90)*pi/180');
blk([S 'Math Operations/Sum'], 'phi - phi mao', [820 520 840 560], 'Inputs', '+-');
blk([S 'Math Operations/Gain'], 'k mao', [870 525 920 555], 'Gain', '-p.hold_k');
blk([S 'Math Operations/Gain'], 'c mao', [870 590 920 620], 'Gain', '-p.hold_c');
blk([S 'Math Operations/Sum'], 'torque mao', [950 540 970 600], 'Inputs', '++');
blk([S 'Math Operations/Product'], 'mao ativa', [1000 450 1030 490]);
blk([S 'Math Operations/Sum'], 'tau_d', [1060 330 1080 470], 'Inputs', '+++');

% ---------------------------------------------------------------- outputs
blk([S 'Math Operations/Gain'], 'rad2deg', [1280 130 1330 160], 'Gain', '180/pi');
blk([S 'Sources/Constant'], '90 graus', [1280 190 1330 220], 'Value', '90');
blk([S 'Math Operations/Sum'], 'theta', [1360 140 1380 200], 'Inputs', '++');
blk([S 'Sinks/Scope'], 'Scope theta', [1420 150 1450 190]);
blk([S 'Sinks/To Workspace'], 'log theta', [1420 220 1480 250], 'VariableName', 'theta', ...
    'SaveFormat', 'Timeseries');
blk([S 'Sinks/To Workspace'], 'log u', [550 140 610 170], 'VariableName', 'u', 'SaveFormat', 'Timeseries');
blk([S 'Sinks/To Workspace'], 'log I', [490 160 550 190], 'VariableName', 'I', 'SaveFormat', 'Timeseries');
blk([S 'Sinks/To Workspace'], 'log F', [850 10 910 40], 'VariableName', 'F', 'SaveFormat', 'Timeseries');

% ---------------------------------------------------------------- wiring
wire('phi_r/1', 'erro/1');
wire('ZOH phi/1', 'erro/2');
wire('erro/1', 'Kp/1');
wire('erro/1', 'Ki/1');
wire('Ki/1', 'Integracao limitada/1');
wire('ZOH rate/1', 'Kd (giroscopio)/1');
wire('Kp/1', 'u = P + I - D/1');
wire('Integracao limitada/1', 'u = P + I - D/2');
wire('Kd (giroscopio)/1', 'u = P + I - D/3');
wire('Integracao limitada/1', 'log I/1');
wire('u = P + I - D/1', 'Limites do atuador/1');
wire('u = P + I - D/1', 'log u/1');
wire('Limites do atuador/1', 'us - F/1');
wire('F/1', 'us - F/2');
wire('us - F/1', 'inv tau_m/1');
wire('inv tau_m/1', 'F/1');
wire('F/1', 'L/1');
wire('F/1', 'log F/1');
wire('L/1', 'torques/1');
wire('phi/1', 'sin/1');
wire('sin/1', 'm g h/1');
wire('m g h/1', 'torques/2');
wire('tau_d/1', 'torques/3');
wire('rate/1', 'b/1');
wire('b/1', 'torques/4');
wire('torques/1', 'inv J/1');
wire('inv J/1', 'rate/1');
wire('rate/1', 'phi/1');
wire('phi/2', 'rate/2');                 % floor contact: rate held at 0 while |phi| = phi_bat
wire('phi/1', 'ZOH phi/1');
wire('rate/1', 'ZOH rate/1');
wire('toque inicio/1', 'tau_d/1');
wire('toque fim/1', 'tau_d/2');
wire('mao pega/1', 'janela mao/1');
wire('mao solta/1', 'janela mao/2');
wire('phi/1', 'phi - phi mao/1');
wire('phi mao/1', 'phi - phi mao/2');
wire('phi - phi mao/1', 'k mao/1');
wire('rate/1', 'c mao/1');
wire('k mao/1', 'torque mao/1');
wire('c mao/1', 'torque mao/2');
wire('janela mao/1', 'mao ativa/1');
wire('torque mao/1', 'mao ativa/2');
wire('mao ativa/1', 'tau_d/3');
wire('phi/1', 'rad2deg/1');
wire('rad2deg/1', 'theta/1');
wire('90 graus/1', 'theta/2');
wire('theta/1', 'Scope theta/1');
wire('theta/1', 'log theta/1');

save_system(mdl, fullfile(here, [mdl '.slx']));
fprintf('Modelo criado: %s\n', fullfile(here, [mdl '.slx']));
end
