/*
 * motor.h - fan module QYF-749 (L9110H H-bridge) on D10/D11 (TIM4_CH1 / TIM3_CH2)
 */
#ifndef MOTOR_H
#define MOTOR_H

extern float motor_deadzone;   /* 0..1, duty needed to start spinning */
extern int   motor_sign;       /* +1 or -1, so that u > 0 increases theta */
extern float motor_duty_max;   /* 0..1, hard cap on |duty| in every mode */

void  motor_set(float u);      /* u in -1..+1 (sign = direction) */
void  motor_set_raw(float duty); /* -1..+1 straight to PWM, no dead-zone compensation */
float motor_duty(void);        /* last duty applied (-1..+1) */

#endif /* MOTOR_H */
