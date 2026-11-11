/*
 * board.c - clock, GPIO, UART2, I2C1 and fan PWM (TIM3, TIM4) initialisation (HAL)
 */
#include "board.h"
#include "config.h"

UART_HandleTypeDef huart2;
I2C_HandleTypeDef  hi2c1;
TIM_HandleTypeDef  htim3;
TIM_HandleTypeDef  htim4;

void error_handler(void)
{
    __disable_irq();
    while (1) {
        /* stay here: LD2 stays off, use the debugger to find the cause */
    }
}

/* 80 MHz from MSI (4 MHz) through the PLL: 4 / 1 * 40 / 2 = 80 MHz */
static void clock_init(void)
{
    RCC_OscInitTypeDef osc = {0};
    RCC_ClkInitTypeDef clk = {0};

    if (HAL_PWREx_ControlVoltageScaling(PWR_REGULATOR_VOLTAGE_SCALE1) != HAL_OK)
        error_handler();

    osc.OscillatorType      = RCC_OSCILLATORTYPE_MSI;
    osc.MSIState            = RCC_MSI_ON;
    osc.MSICalibrationValue = RCC_MSICALIBRATION_DEFAULT;
    osc.MSIClockRange       = RCC_MSIRANGE_6;          /* 4 MHz */
    osc.PLL.PLLState        = RCC_PLL_ON;
    osc.PLL.PLLSource       = RCC_PLLSOURCE_MSI;
    osc.PLL.PLLM            = 1;
    osc.PLL.PLLN            = 40;
    osc.PLL.PLLP            = RCC_PLLP_DIV7;
    osc.PLL.PLLQ            = RCC_PLLQ_DIV2;
    osc.PLL.PLLR            = RCC_PLLR_DIV2;
    if (HAL_RCC_OscConfig(&osc) != HAL_OK)
        error_handler();

    clk.ClockType      = RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_SYSCLK |
                         RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2;
    clk.SYSCLKSource   = RCC_SYSCLKSOURCE_PLLCLK;
    clk.AHBCLKDivider  = RCC_SYSCLK_DIV1;
    clk.APB1CLKDivider = RCC_HCLK_DIV1;
    clk.APB2CLKDivider = RCC_HCLK_DIV1;
    if (HAL_RCC_ClockConfig(&clk, FLASH_LATENCY_4) != HAL_OK)
        error_handler();
}

/* LD2 (PA5) as a heartbeat LED */
static void gpio_init(void)
{
    GPIO_InitTypeDef g = {0};

    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_GPIOB_CLK_ENABLE();

    g.Pin   = GPIO_PIN_5;
    g.Mode  = GPIO_MODE_OUTPUT_PP;
    g.Pull  = GPIO_NOPULL;
    g.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(GPIOA, &g);
}

/* USART2: PA2 = TX, PA3 = RX (connected to the ST-LINK virtual COM port) */
static void uart2_init(void)
{
    GPIO_InitTypeDef g = {0};

    __HAL_RCC_USART2_CLK_ENABLE();
    g.Pin       = GPIO_PIN_2 | GPIO_PIN_3;
    g.Mode      = GPIO_MODE_AF_PP;
    g.Pull      = GPIO_NOPULL;
    g.Speed     = GPIO_SPEED_FREQ_VERY_HIGH;
    g.Alternate = GPIO_AF7_USART2;
    HAL_GPIO_Init(GPIOA, &g);

    huart2.Instance        = USART2;
    huart2.Init.BaudRate   = UART_BAUD;
    huart2.Init.WordLength = UART_WORDLENGTH_8B;
    huart2.Init.StopBits   = UART_STOPBITS_1;
    huart2.Init.Parity     = UART_PARITY_NONE;
    huart2.Init.Mode       = UART_MODE_TX_RX;
    huart2.Init.HwFlowCtl  = UART_HWCONTROL_NONE;
    huart2.Init.OverSampling = UART_OVERSAMPLING_16;
    if (HAL_UART_Init(&huart2) != HAL_OK)
        error_handler();

    HAL_NVIC_SetPriority(USART2_IRQn, 1, 0);
    HAL_NVIC_EnableIRQ(USART2_IRQn);
}

/* I2C1: PB8 = SCL (D15), PB9 = SDA (D14) */
static void i2c1_init(void)
{
    GPIO_InitTypeDef g = {0};

    __HAL_RCC_I2C1_CLK_ENABLE();
    g.Pin       = GPIO_PIN_8 | GPIO_PIN_9;
    g.Mode      = GPIO_MODE_AF_OD;
    g.Pull      = GPIO_PULLUP;      /* the Grove module also has pull-ups */
    g.Speed     = GPIO_SPEED_FREQ_HIGH;
    g.Alternate = GPIO_AF4_I2C1;
    HAL_GPIO_Init(GPIOB, &g);

    hi2c1.Instance              = I2C1;
    hi2c1.Init.Timing           = I2C_TIMING_100K;
    hi2c1.Init.OwnAddress1      = 0;
    hi2c1.Init.AddressingMode   = I2C_ADDRESSINGMODE_7BIT;
    hi2c1.Init.DualAddressMode  = I2C_DUALADDRESS_DISABLE;
    hi2c1.Init.GeneralCallMode  = I2C_GENERALCALL_DISABLE;
    hi2c1.Init.NoStretchMode    = I2C_NOSTRETCH_DISABLE;
    if (HAL_I2C_Init(&hi2c1) != HAL_OK)
        error_handler();
    HAL_I2CEx_ConfigAnalogFilter(&hi2c1, I2C_ANALOGFILTER_ENABLE);
}

/* fan PWM at 20 kHz on two timers (no single timer reaches both pins):
 *   INA -> D10 = PB6 = TIM4_CH1,  INB -> D11 = PA7 = TIM3_CH2 */
static void pwm_init(TIM_HandleTypeDef *h, TIM_TypeDef *tim, uint32_t channel)
{
    TIM_OC_InitTypeDef oc = {0};

    h->Instance               = tim;
    h->Init.Prescaler         = 0;
    h->Init.CounterMode       = TIM_COUNTERMODE_UP;
    h->Init.Period            = PWM_ARR;
    h->Init.ClockDivision     = TIM_CLOCKDIVISION_DIV1;
    h->Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_ENABLE;
    if (HAL_TIM_PWM_Init(h) != HAL_OK)
        error_handler();

    oc.OCMode     = TIM_OCMODE_PWM1;
    oc.Pulse      = 0;
    oc.OCPolarity = TIM_OCPOLARITY_HIGH;
    oc.OCFastMode = TIM_OCFAST_DISABLE;
    if (HAL_TIM_PWM_ConfigChannel(h, &oc, channel) != HAL_OK)
        error_handler();
    HAL_TIM_PWM_Start(h, channel);
}

static void fan_pwm_init(void)
{
    GPIO_InitTypeDef g = {0};

    __HAL_RCC_TIM3_CLK_ENABLE();
    __HAL_RCC_TIM4_CLK_ENABLE();
    pwm_init(&htim4, TIM4, TIM_CHANNEL_1);
    pwm_init(&htim3, TIM3, TIM_CHANNEL_2);

    /* pins switched to the timers only after both outputs are at 0 % */
    g.Mode      = GPIO_MODE_AF_PP;
    g.Pull      = GPIO_NOPULL;
    g.Speed     = GPIO_SPEED_FREQ_LOW;
    g.Alternate = GPIO_AF2_TIM4;
    g.Pin       = GPIO_PIN_6;
    HAL_GPIO_Init(GPIOB, &g);
    g.Alternate = GPIO_AF2_TIM3;
    g.Pin       = GPIO_PIN_7;
    HAL_GPIO_Init(GPIOA, &g);
}

/* duty of each H-bridge input, 0..PWM_ARR+1 */
void board_fan_pwm(uint32_t ccr_a, uint32_t ccr_b)
{
    __HAL_TIM_SET_COMPARE(&htim4, TIM_CHANNEL_1, ccr_a);
    __HAL_TIM_SET_COMPARE(&htim3, TIM_CHANNEL_2, ccr_b);
}

void board_init(void)
{
    HAL_Init();
    clock_init();
    gpio_init();
    uart2_init();
    i2c1_init();
    fan_pwm_init();
}
