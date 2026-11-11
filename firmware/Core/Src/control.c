/*
 * control.c - PID with limited integration
 *
 *   e = ref - theta
 *   I = clamp(I + Ki*dt*e, Imin, Imax)     <- limited integration
 *   D = -Kd * rate                         <- derivative on the measurement (gyro)
 *   u = Kp*e + I + D,  u_sat = clamp(u, Umin, Umax)
 */
#include "control.h"
#include "config.h"

pidc_t pid = {
    .kp = KP_DEFAULT, .ki = KI_DEFAULT, .kd = KD_DEFAULT,
    .i_min = I_MIN_DEFAULT, .i_max = I_MAX_DEFAULT,
    .u_min = U_MIN_DEFAULT, .u_max = U_MAX_DEFAULT,
    .ref = REF_DEFAULT_DEG,
};

static float clamp(float x, float lo, float hi)
{
    if (x < lo) return lo;
    if (x > hi) return hi;
    return x;
}

void pid_reset(pidc_t *c)
{
    c->i = 0.0f;
    c->u = 0.0f;
    c->u_sat = 0.0f;
}

float pid_step(pidc_t *c, float theta, float rate, float dt)
{
    float e = c->ref - theta;

    c->i = clamp(c->i + c->ki * dt * e, c->i_min, c->i_max);
    c->u = c->kp * e + c->i - c->kd * rate;
    c->u_sat = clamp(c->u, c->u_min, c->u_max);
    return c->u_sat;
}
