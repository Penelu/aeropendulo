function out = simula_aeropendulo(p, c)
% SIMULA_AEROPENDULO  Nonlinear aeropendulum + digital PID with limited integration.
% Same equations as the Simulink model (cria_modelo_aeropendulo.m); runs in
% MATLAB and GNU Octave without toolboxes, so it can validate the Simulink results.
%
%   J*phi'' = m*g*h*sin(phi) - b*phi' + L*F + tau_d     (rod, phi = theta - 90 deg)
%   tau_d   = touch pulse + hand (spring-damper towards hold_theta, from hold_t0 to hold_t1)
%   tau_m*F' = sat(u, Fmin, Fmax) - F                   (fan, first order)
%   I[k] = clamp(I[k-1] + Ki*Ts*e[k], Imin, Imax)       (limited integration)
%   u[k] = Kp*e[k] + I[k] - Kd*phi'[k]                  (D on the gyro rate)
%
% p : parameters (parametros_aeropendulo.m)
% c : case  .Fmin .Fmax (actuator limits, N)  .Imin .Imax (integrator limits, N)
% out: .t .theta (deg) .u .us .F .I (N) .fell (true if the rod hit the floor)

n     = round(p.Tend / p.dt);
nCtrl = round(p.Ts / p.dt);
phi_r = (p.theta_r - 90) * pi/180;

% start at rest on the reference, holding thrust already applied
Fh  = -p.m*p.g*p.h*sin(phi_r) / p.L;
phi = phi_r;  w = 0;  F = Fh;  I = min(max(Fh, c.Imin), c.Imax);  u = Fh;

out.t = (0:n-1)' * p.dt;
[out.theta, out.u, out.us, out.F, out.I] = deal(zeros(n, 1));
out.fell = false;

for k = 1:n
    t = out.t(k);
    if mod(k - 1, nCtrl) == 0                       % controller, every Ts
        e = phi_r - phi;
        I = min(max(I + p.Ki*p.Ts*e, c.Imin), c.Imax);
        u = p.Kp*e + I - p.Kd*w;
    end
    us = min(max(u, c.Fmin), c.Fmax);               % actuator limits

    tau_d = p.td_amp * (t >= p.td_t0 && t < p.td_t0 + p.td_dur);
    if t >= p.hold_t0 && t < p.hold_t1               % hand holding the rod
        tau_d = tau_d - p.hold_k*(phi - (p.hold_theta - 90)*pi/180) - p.hold_c*w;
    end
    acc = (p.m*p.g*p.h*sin(phi) - p.b*w + p.L*F + tau_d) / p.J;

    w   = w + acc*p.dt;                             % Euler integration
    phi = phi + w*p.dt;
    F   = F + (us - F)/p.tau_m*p.dt;

    if abs(phi) >= p.phi_bat                        % floor stop: rod lies down
        phi = sign(phi)*p.phi_bat;  w = 0;  out.fell = true;
    end

    out.theta(k) = 90 + phi*180/pi;
    out.u(k) = u;  out.us(k) = us;  out.F(k) = F;  out.I(k) = I;
end
end
