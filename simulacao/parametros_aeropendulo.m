% PARAMETROS_AEROPENDULO  Model, actuator and controller parameters (SI units).
% Used by the Simulink model (cria_modelo_aeropendulo.m / roda_simulink.m) and by
% the script simulation (simula_aeropendulo.m / compara_casos.m).
%
% Rod: PLA design of the anti-windup article (target of the next prototype).
% Fan: values MEASURED on the bench (2026-11-08, 5 V supply, stronger spin direction).

p.m     = 0.145;      % total mass (kg)
p.g     = 9.81;       % gravity (m/s^2)
p.h     = 0.069;      % centre of mass height (m)
p.L     = 0.212;      % thrust height (m)
p.J     = 1.10e-3;    % inertia about the pivot (kg.m^2)
p.b     = 5e-4;       % viscous friction (N.m.s/rad)
p.tau_m = 0.03;       % fan time constant (s), estimate
p.phi_bat = 24*pi/180;% floor stop (rad from vertical)

p.Fmax  = 9e-3*9.81;  % measured max thrust: 9 gf = 0.088 N at 90 % duty
p.Fmin  = 0;          % forward only (reversing overheated the L9110H)

% PID by pole placement on the linear model (same design as the article)
K  = p.L/p.J;  a1 = p.b/p.J;  a0 = p.m*p.g*p.h/p.J;
wn = 8;  zeta = 0.9;  alpha = 2;
p.Kp = (wn^2*(1 + 2*zeta*alpha) + a0) / K;     % N/rad
p.Ki = alpha*wn^3 / K;                          % N/(rad.s)
p.Kd = (2*zeta*wn + alpha*wn - a1) / K;         % N.s/rad
p.Ts = 5e-3;          % controller period (s), same as the firmware (200 Hz)

% operating point and limited integration bounds
p.theta_r   = 85;                       % reference (deg); fan holds against gravity
p.phi_r     = (p.theta_r - 90)*pi/180;  % reference as deviation from vertical (rad)
p.Fh        = -p.m*p.g*p.h*sin(p.phi_r)/p.L;   % holding thrust at the reference (N)
theta_range = [83 88];                  % operating range (deg)
Fh_range = p.m*p.g*p.h*sin((90 - theta_range)*pi/180) / p.L;   % holding thrust (N)
mu = 0.25;                              % 25 % margin
p.Imin = 0;                             % forward-only actuator
p.Imax = min(p.Fmax, (1 + mu)*max(Fh_range));

% disturbances
% (1) hand holding the rod below the reference, then releasing it: the way the
%     prototype is started with button B1 (fan saturated while the hand holds it)
p.hold_theta = 82;    % angle where the hand holds the rod (deg)
p.hold_t0    = 0.5;   % hand grabs the rod (s)
p.hold_t1    = 2.0;   % hand releases the rod (s)
p.hold_k     = 1.0;   % hand stiffness (N.m/rad)
p.hold_c     = 0.05;  % hand damping (N.m.s/rad)
% (2) short touch pushing the rod towards the floor (off by default)
p.td_amp = 0;         % torque (N.m), e.g. -0.006
p.td_t0  = 0.5;       % start (s)
p.td_dur = 0.2;       % duration (s)
p.dt     = 5e-4;      % integration step (s)
p.Tend   = 4;         % simulation time (s)
