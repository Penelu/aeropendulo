/*
 * imu.c - accelerometer/gyroscope driver and angle estimation
 *
 * The ICM20600 (current Grove IMU 9DOF) and the MPU-9250 (older version)
 * share the same register map for what is used here.
 */
#include "imu.h"
#include "board.h"
#include "config.h"
#include <math.h>

/* registers (MPU-6xxx / MPU-9250 / ICM-206xx family) */
#define REG_SMPLRT_DIV    0x19
#define REG_CONFIG        0x1A
#define REG_GYRO_CONFIG   0x1B
#define REG_ACCEL_CONFIG  0x1C
#define REG_ACCEL_CONFIG2 0x1D
#define REG_ACCEL_XOUT_H  0x3B
#define REG_PWR_MGMT_1    0x6B
#define REG_PWR_MGMT_2    0x6C
#define REG_WHO_AM_I      0x75

#define ACC_LSB_PER_G     8192.0f   /* +/-4 g     */
#define GYRO_LSB_PER_DPS  65.5f     /* +/-500 dps */
#define RAD2DEG           57.29578f

imu_axes_t imu_axes = {
    AXIS_UP_DEFAULT, SIGN_UP_DEFAULT,
    AXIS_SIDE_DEFAULT, SIGN_SIDE_DEFAULT,
    AXIS_GYRO_DEFAULT, SIGN_GYRO_DEFAULT,
};

static uint8_t addr;                 /* 7-bit address */
static uint8_t whoami;
static float gyro_bias[3];

static bool wr(uint8_t reg, uint8_t val)
{
    return HAL_I2C_Mem_Write(&hi2c1, addr << 1, reg, 1, &val, 1, 10) == HAL_OK;
}

static bool rd(uint8_t reg, uint8_t *buf, uint16_t n)
{
    return HAL_I2C_Mem_Read(&hi2c1, addr << 1, reg, 1, buf, n, 10) == HAL_OK;
}

const char *imu_name(void)
{
    switch (whoami) {
    case 0x11: return "ICM-20600";
    case 0x12: return "ICM-20602";
    case 0x71: return "MPU-9250";
    case 0x73: return "MPU-9255";
    case 0x68: return "MPU-6050/9150";
    default:   return "unknown";
    }
}

uint8_t imu_address(void) { return addr; }
uint8_t imu_whoami(void)  { return whoami; }

bool imu_init(void)
{
    const uint8_t candidates[] = {0x69, 0x68};   /* Grove default is 0x69 */

    addr = 0;
    for (unsigned i = 0; i < sizeof candidates; i++) {
        if (HAL_I2C_IsDeviceReady(&hi2c1, candidates[i] << 1, 3, 10) == HAL_OK) {
            addr = candidates[i];
            break;
        }
    }
    if (addr == 0)
        return false;

    if (!rd(REG_WHO_AM_I, &whoami, 1))
        return false;

    wr(REG_PWR_MGMT_1, 0x80);     /* reset */
    HAL_Delay(100);
    wr(REG_PWR_MGMT_1, 0x01);     /* wake up, best clock source */
    HAL_Delay(10);
    wr(REG_PWR_MGMT_2, 0x00);     /* accel + gyro on */
    wr(REG_SMPLRT_DIV, 0x00);     /* 1 kHz internal rate */
    wr(REG_CONFIG, 0x03);         /* gyro low-pass ~41 Hz */
    wr(REG_GYRO_CONFIG, 0x08);    /* +/-500 dps */
    wr(REG_ACCEL_CONFIG, 0x08);   /* +/-4 g */
    if (whoami != 0x68)
        wr(REG_ACCEL_CONFIG2, 0x03);  /* accel low-pass ~44 Hz */
    HAL_Delay(50);
    return true;
}

bool imu_read(imu_raw_t *r)
{
    uint8_t b[14];
    if (!rd(REG_ACCEL_XOUT_H, b, sizeof b))
        return false;

    for (int i = 0; i < 3; i++) {
        int16_t a = (int16_t)((b[2 * i] << 8) | b[2 * i + 1]);
        int16_t g = (int16_t)((b[8 + 2 * i] << 8) | b[8 + 2 * i + 1]);
        r->acc[i]  = a / ACC_LSB_PER_G;
        r->gyro[i] = g / GYRO_LSB_PER_DPS - gyro_bias[i];
    }
    return true;
}

void imu_calibrate_gyro(int samples)
{
    float sum[3] = {0, 0, 0};
    imu_raw_t r;
    int n = 0;

    gyro_bias[0] = gyro_bias[1] = gyro_bias[2] = 0;
    for (int k = 0; k < samples; k++) {
        if (imu_read(&r)) {
            for (int i = 0; i < 3; i++)
                sum[i] += r.gyro[i];
            n++;
        }
        HAL_Delay(2);
    }
    if (n > 0)
        for (int i = 0; i < 3; i++)
            gyro_bias[i] = sum[i] / n;
}

/* angle from gravity only: 90 deg when the UP axis is vertical */
static float accel_angle(const imu_raw_t *r)
{
    float up   = imu_axes.sign_up   * r->acc[imu_axes.axis_up];
    float side = imu_axes.sign_side * r->acc[imu_axes.axis_side];
    return atan2f(up, side) * RAD2DEG;
}

void imu_angle_reset(imu_angle_t *a, const imu_raw_t *r)
{
    a->theta_acc  = accel_angle(r);
    a->rate       = imu_axes.sign_gyro * r->gyro[imu_axes.axis_gyro];
    a->theta_gyro = a->theta_acc;
    a->theta      = a->theta_acc;
}

void imu_angle_update(imu_angle_t *a, const imu_raw_t *r, float dt)
{
    const float alpha = COMP_TAU_S / (COMP_TAU_S + dt);

    a->theta_acc   = accel_angle(r);
    a->rate        = imu_axes.sign_gyro * r->gyro[imu_axes.axis_gyro];
    a->theta_gyro += a->rate * dt;
    /* complementary filter: gyro for fast changes, accelerometer for the mean */
    a->theta = alpha * (a->theta + a->rate * dt) + (1.0f - alpha) * a->theta_acc;
}
