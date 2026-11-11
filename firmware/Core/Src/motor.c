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
int   motor_sign = +1;

static float last_duty;

void motor_set_raw(float duty)
{
    if (duty > 1.0f)  duty = 1.0f;
    if (duty < -1.0f) duty = -1.0f;
    last_duty = duty;

    uint32_t ccr = (uint32_t)(fabsf(duty) * (PWM_ARR + 1));
    if (duty >= 0.0f) {
        __HAL_TIM_SET_COMPARE(&htim3, TIM_CHANNEL_2, 0);
        __HAL_TIM_SET_COMPARE(&htim3, TIM_CHANNEL_1, ccr);
    } else {
        __HAL_TIM_SET_COMPARE(&htim3, TIM_CHANNEL_1, 0);
        __HAL_TIM_SET_COMPARE(&htim3, TIM_CHANNEL_2, ccr);
    }
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
