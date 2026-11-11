/*
 * config.h - Aeropendulo project settings (NUCLEO-L476RG)
 *
 * Wiring (Arduino header names printed on the Nucleo board):
 *   IMU (MPU-9250) : VCC -> 3V3, GND -> GND, SDA -> D14 (PB9), SCL -> D15 (PB8)
 *   Fan (L9110H)   : INA -> D10 (PB6, TIM4_CH1), INB -> D11 (PA7, TIM3_CH2)
 *                    VCC -> external supply, GND -> Nucleo GND (common ground!)
 *   PC             : USB cable of the Nucleo (ST-LINK virtual COM port, USART2)
 */
#ifndef CONFIG_H
#define CONFIG_H

/* ---- Timing ---- */
#define LOOP_PERIOD_MS      5       /* control loop: 200 Hz */
#define TELEMETRY_DIV       4       /* telemetry every 4 loops: 50 Hz */
#define UART_BAUD           115200

/* ---- I2C ---- */
#define I2C_TIMING_100K     0x10909CECu   /* 100 kHz with PCLK1 = 80 MHz */

/* ---- PWM (TIM3 and TIM4 at 80 MHz, PSC = 0) ---- */
#define PWM_ARR             3999u   /* 80 MHz / 4000 = 20 kHz (inaudible) */

/* ---- IMU axis mapping (can be changed at run time with "axes") ----
 * Axis index: 0 = X, 1 = Y, 2 = Z. Sign: +1 or -1.
 * UP   : accelerometer axis along the rod, pointing up
 * SIDE : accelerometer axis perpendicular to the rod, in the swing plane
 * GYRO : gyroscope axis parallel to the pivot (line between the two feet)
 */
#define AXIS_UP_DEFAULT     2       /* measured on the rod: axes +z -y +x */
#define SIGN_UP_DEFAULT     (+1)
#define AXIS_SIDE_DEFAULT   1
#define SIGN_SIDE_DEFAULT   (-1)
#define AXIS_GYRO_DEFAULT   0
#define SIGN_GYRO_DEFAULT   (+1)

/* ---- Angle estimation ---- */
#define COMP_TAU_S          0.5f    /* complementary filter time constant */

/* ---- Controller defaults (u is normalised: -1..+1 = full reverse..full forward) ---- */
#define REF_DEFAULT_DEG     85.0f   /* forward-only fan: lean so the fan holds against gravity */
#define REF_MIN_DEG         70.0f
#define REF_MAX_DEG         110.0f
#define BUTTON_DEBOUNCE_MS  50      /* B1: press = hold current angle / stop */
/* starting point scaled from the anti-windup article model; tune on the rod */
#define KP_DEFAULT          0.120f  /* 1/deg       */
#define KI_DEFAULT          0.300f  /* 1/(deg.s)   */
#define KD_DEFAULT          0.010f  /* 1/(deg/s)   */
#define I_MIN_DEFAULT       (0.0f)   /* limited integration bounds (no negative I: u >= 0) */
#define I_MAX_DEFAULT       (+0.40f)
#define U_MIN_DEFAULT       (0.0f)   /* actuator limits: fan forward only (reversing overheats the L9110H) */
#define U_MAX_DEFAULT       (+1.0f)
#define DEADZONE_DEFAULT    0.25f    /* duty below which the fan does not spin (starts at ~30 %) */
#define DUTY_MAX_DEFAULT    0.90f    /* hard duty cap: 90 % on 5 V to limit the L9110H heating (55 on 9 V) */
#define MOTOR_SIGN_DEFAULT  (-1)     /* measured: with +1 the fan pushed the rod into the fall */
#define FALL_LIMIT_DEG      30.0f    /* motor off if |theta - 90| > this */

#endif /* CONFIG_H */
