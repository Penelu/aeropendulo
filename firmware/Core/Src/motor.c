/*
 * motor.c - fan drive through the L9110H
 *
 *   forward : INA = PWM, INB = 0
 *   reverse : INA = 0,   INB = PWM
 *   off     : INA = 0,   INB = 0 (coast)
 */
#include "motor.h"
#include "board.h"
#include "config.h"
#include <math.h>

float motor_deadzone = DEADZONE_DEFAULT;
int   motor_sign = MOTOR_SIGN_DEFAULT;
float motor_duty_max = DUTY_MAX_DEFAULT;

static float last_duty;

void motor_set_raw(float duty)
{
    /* hard cap for every mode: protects the 5 V motor on a higher supply */
    if (duty > motor_duty_max)  duty = motor_duty_max;
    if (duty < -motor_duty_max) duty = -motor_duty_max;
    last_duty = duty;

    uint32_t ccr = (uint32_t)(fabsf(duty) * (PWM_ARR + 1));
    if (duty >= 0.0f)
        board_fan_pwm(ccr, 0);
    else
        board_fan_pwm(0, ccr);
}

/* dead-zone compensation: any small non-zero command starts the fan */
void motor_set(float u)
{
    float a = fabsf(u);
    float duty = 0.0f;

    if (a > 0.005f) {
        if (a > 1.0f) a = 1.0f;
        duty = motor_deadzone + (1.0f - motor_deadzone) * a;
        if (u < 0.0f) duty = -duty;
    }
    motor_set_raw(motor_sign * duty);
}

float motor_duty(void)
{
    return last_duty;
}
