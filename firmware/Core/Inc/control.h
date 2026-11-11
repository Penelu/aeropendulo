/*
 * control.h - PID with limited integration (anti-windup)
 */
#ifndef CONTROL_H
#define CONTROL_H

typedef struct {
    float kp, ki, kd;
    float i_min, i_max;     /* limited integration bounds */
    float u_min, u_max;     /* actuator limits */
    float ref;              /* reference angle (deg) */
    float i;                /* integral term state */
    float u;                /* last computed command (before saturation) */
    float u_sat;            /* last applied command */
} pidc_t;

extern pidc_t pid;

void  pid_reset(pidc_t *c);
float pid_step(pidc_t *c, float theta, float rate, float dt);

#endif /* CONTROL_H */
