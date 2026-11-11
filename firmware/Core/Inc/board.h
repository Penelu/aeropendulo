/*
 * board.h - peripheral handles shared between modules
 */
#ifndef BOARD_H
#define BOARD_H

#include "stm32l4xx_hal.h"
#include <stdbool.h>

extern UART_HandleTypeDef huart2;   /* ST-LINK virtual COM port */
extern I2C_HandleTypeDef  hi2c1;    /* IMU */
extern TIM_HandleTypeDef  htim3;    /* fan PWM, INB */
extern TIM_HandleTypeDef  htim4;    /* fan PWM, INA */

void board_init(void);
void error_handler(void);
bool board_button(void);           /* true while the blue user button B1 is pressed */
void board_fan_pwm(uint32_t ccr_a, uint32_t ccr_b);  /* INA, INB compare values */

#endif /* BOARD_H */
