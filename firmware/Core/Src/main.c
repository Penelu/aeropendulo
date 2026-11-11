/*
 * main.c - Aeropendulo firmware (NUCLEO-L476RG)
 *
 * A wooden rod stands on two rounded feet, so it can only tilt about one axis.
 * A fan (QYF-749 + L9110H) on the top pushes it back to the reference angle
 * measured by the Grove IMU 9DOF. PID with limited integration (anti-windup).
 *
 * Serial console on the ST-LINK virtual COM port, 115200 8N1. Type "help".
 * Telemetry lines start with a letter and a comma so the PC app can parse them:
 *   I,ax,ay,az,gx,gy,gz,theta_acc,theta_gyro,theta    (imu test, 20 Hz)
 *   D,t_ms,theta,ref,u,i,duty,theta_acc,rate          (motor / control, 50 Hz)
 */
#include "board.h"
#include "config.h"
#include "serial.h"
#include "imu.h"
#include "motor.h"
#include "control.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

typedef enum { MODE_IDLE, MODE_IMU, MODE_OPEN, MODE_RAMP, MODE_RUN } mode_t_;

static mode_t_ mode = MODE_IDLE;
static imu_raw_t raw;
static imu_angle_t ang;
static bool imu_ok;
static int imu_errors;

/* ramp test state */
static int ramp_step;
static uint32_t ramp_t0;
#define RAMP_STEP_MS 1500

/* ------------------------------------------------------------------ */
static void stop_all(void)
{
    motor_set_raw(0.0f);
    pid_reset(&pid);
    mode = MODE_IDLE;
}

static void start_run(void)
{
    if (!imu_ok) {
        serial_printf("IMU not found, cannot run\r\n");
        return;
    }
    pid_reset(&pid);
    mode = MODE_RUN;
    serial_printf("run: ref %.1f\r\n", pid.ref);
}

/* user button B1 (polled every loop): idle -> hold the current angle, running -> stop */
static void button_update(void)
{
    static bool pressed;
    static int count;
    bool now = board_button();

    count = (now == pressed) ? 0 : count + 1;
    if (count < BUTTON_DEBOUNCE_MS / LOOP_PERIOD_MS)
        return;
    pressed = now;
    count = 0;
    if (!pressed)
        return;                         /* act on the press, not on the release */

    if (mode == MODE_RUN) {
        stop_all();
        serial_printf("button: stopped\r\n");
    } else if (ang.theta < REF_MIN_DEG || ang.theta > REF_MAX_DEG) {
        stop_all();
        serial_printf("button: theta %.1f outside %.0f..%.0f, not started\r\n",
                      ang.theta, REF_MIN_DEG, REF_MAX_DEG);
    } else {
        stop_all();                     /* leaves imu/motor/ramp test modes */
        pid.ref = ang.theta;
        serial_printf("button: ");
        start_run();
    }
}

static void print_help(void)
{
    serial_printf("\r\nAeropendulo - commands:\r\n");
    serial_printf("  scan              I2C bus scan\r\n");
    serial_printf("  imu               stream accel/gyro/angles (I lines)\r\n");
    serial_printf("  cal               gyro bias calibration (keep the rod still)\r\n");
    serial_printf("  axes U S G        axes, e.g. axes +x +y +z (up, side, gyro)\r\n");
    serial_printf("  motor P           open-loop duty P%% (-100..100)\r\n");
    serial_printf("  ramp              duty ramp 10..100%% both directions\r\n");
    serial_printf("  dz P | msign S    dead-zone %% | motor sign (+1/-1)\r\n");
    serial_printf("  dmax P            duty cap %% in every mode (55 on a 9 V supply)\r\n");
    serial_printf("  run | stop        closed loop on | everything off\r\n");
    serial_printf("  ref D             reference angle in deg (90 = vertical)\r\n");
    serial_printf("  pid KP KI KD      gains (u per deg, per deg.s, per deg/s)\r\n");
    serial_printf("  ilim MIN MAX      limited integration bounds (-1..1)\r\n");
    serial_printf("  ulim MIN MAX      actuator limits (-1..1)\r\n");
    serial_printf("  status            show settings\r\n");
    serial_printf("  blue button B1    hold the current angle (ref = theta, run) | stop\r\n");
}

static void print_status(void)
{
    serial_printf("IMU: %s (WHO_AM_I 0x%02X) at 0x%02X, errors %d\r\n",
                  imu_ok ? imu_name() : "NOT FOUND", imu_whoami(), imu_address(), imu_errors);
    serial_printf("axes: up %c%c side %c%c gyro %c%c | theta %.1f deg\r\n",
                  imu_axes.sign_up > 0 ? '+' : '-', 'x' + imu_axes.axis_up,
                  imu_axes.sign_side > 0 ? '+' : '-', 'x' + imu_axes.axis_side,
                  imu_axes.sign_gyro > 0 ? '+' : '-', 'x' + imu_axes.axis_gyro, ang.theta);
    serial_printf("pid: kp %.4f ki %.4f kd %.4f | ref %.1f\r\n", pid.kp, pid.ki, pid.kd, pid.ref);
    serial_printf("ilim [%.2f %.2f] ulim [%.2f %.2f] dz %.0f%% msign %+d dmax %.0f%%\r\n",
                  pid.i_min, pid.i_max, pid.u_min, pid.u_max, motor_deadzone * 100, motor_sign,
                  motor_duty_max * 100);
}

static void i2c_scan(void)
{
    serial_printf("I2C scan:");
    for (uint8_t a = 0x08; a < 0x78; a++)
        if (HAL_I2C_IsDeviceReady(&hi2c1, a << 1, 2, 5) == HAL_OK)
            serial_printf(" 0x%02X", a);
    serial_printf("\r\n(MPU-9250 = 0x68, ICM20600 = 0x69 or 0x68)\r\n");
}

/* "+x" -> axis 0, sign +1 ; returns false on a bad token */
static bool parse_axis(const char *s, int *axis, int *sign)
{
    if (!s || strlen(s) != 2 || (s[0] != '+' && s[0] != '-'))
        return false;
    if (s[1] < 'x' || s[1] > 'z')
        return false;
    *sign = (s[0] == '+') ? 1 : -1;
    *axis = s[1] - 'x';
    return true;
}

static float arg_f(char **tok_ok, bool *ok)
{
    char *t = strtok(NULL, " ");
    if (!t) { *ok = false; return 0.0f; }
    (void)tok_ok;
    return strtof(t, NULL);
}

static void handle_command(char *cmd)
{
    char *c = strtok(cmd, " ");
    bool ok = true;
    if (!c)
        return;

    if (!strcmp(c, "help")) {
        print_help();
    } else if (!strcmp(c, "scan")) {
        i2c_scan();
    } else if (!strcmp(c, "status")) {
        print_status();
    } else if (!strcmp(c, "stop")) {
        stop_all();
        serial_printf("stopped\r\n");
    } else if (!strcmp(c, "imu")) {
        stop_all();
        if (!imu_ok) {
            serial_printf("IMU not found, check wiring and reset the board\r\n");
            return;
        }
        imu_angle_reset(&ang, &raw);
        mode = MODE_IMU;
        serial_printf("I,ax,ay,az,gx,gy,gz,theta_acc,theta_gyro,theta\r\n");
    } else if (!strcmp(c, "cal")) {
        stop_all();
        serial_printf("calibrating gyro, keep still...\r\n");
        imu_calibrate_gyro(500);
        imu_read(&raw);
        imu_angle_reset(&ang, &raw);
        serial_printf("done\r\n");
    } else if (!strcmp(c, "axes")) {
        imu_axes_t a = imu_axes;
        ok = parse_axis(strtok(NULL, " "), &a.axis_up, &a.sign_up)
          && parse_axis(strtok(NULL, " "), &a.axis_side, &a.sign_side)
          && parse_axis(strtok(NULL, " "), &a.axis_gyro, &a.sign_gyro);
        if (ok) {
            imu_axes = a;
            imu_angle_reset(&ang, &raw);
            print_status();
        }
    } else if (!strcmp(c, "motor")) {
        float p = arg_f(NULL, &ok);
        if (ok) {
            pid_reset(&pid);
            mode = MODE_OPEN;
            motor_set_raw(motor_sign * p / 100.0f);
            serial_printf("duty %.0f%%\r\n", motor_duty() * 100);   /* after the cap */
        }
    } else if (!strcmp(c, "ramp")) {
        pid_reset(&pid);
        mode = MODE_RAMP;
        ramp_step = 0;
        ramp_t0 = HAL_GetTick() - RAMP_STEP_MS;
    } else if (!strcmp(c, "dz")) {
        float p = arg_f(NULL, &ok);
        if (ok) motor_deadzone = fminf(fmaxf(p / 100.0f, 0.0f), 0.9f);
    } else if (!strcmp(c, "dmax")) {
        float p = arg_f(NULL, &ok);
        if (ok) motor_duty_max = fminf(fmaxf(p / 100.0f, 0.0f), 1.0f);
    } else if (!strcmp(c, "msign")) {
        float s = arg_f(NULL, &ok);
        if (ok) motor_sign = (s < 0) ? -1 : 1;
    } else if (!strcmp(c, "ref")) {
        float r = arg_f(NULL, &ok);
        if (ok) pid.ref = fminf(fmaxf(r, REF_MIN_DEG), REF_MAX_DEG);
    } else if (!strcmp(c, "pid")) {
        float kp = arg_f(NULL, &ok), ki = arg_f(NULL, &ok), kd = arg_f(NULL, &ok);
        if (ok) { pid.kp = kp; pid.ki = ki; pid.kd = kd; }
    } else if (!strcmp(c, "ilim")) {
        float lo = arg_f(NULL, &ok), hi = arg_f(NULL, &ok);
        if (ok) { pid.i_min = lo; pid.i_max = hi; }
    } else if (!strcmp(c, "ulim")) {
        float lo = arg_f(NULL, &ok), hi = arg_f(NULL, &ok);
        if (ok) { pid.u_min = lo; pid.u_max = hi; }
    } else if (!strcmp(c, "run")) {
        start_run();
    } else {
        serial_printf("unknown command '%s' (type help)\r\n", c);
        return;
    }
    if (!ok)
        serial_printf("missing/invalid argument (type help)\r\n");
}

/* one ramp step every RAMP_STEP_MS: +10..+100 %, then -10..-100 %, then stop */
static void ramp_update(void)
{
    if (HAL_GetTick() - ramp_t0 < RAMP_STEP_MS)
        return;
    ramp_t0 = HAL_GetTick();
    ramp_step++;
    if (ramp_step > 20) {
        stop_all();
        serial_printf("ramp done\r\n");
        return;
    }
    float duty = (ramp_step <= 10) ? ramp_step * 0.1f : -(ramp_step - 10) * 0.1f;
    motor_set_raw(motor_sign * duty);
    serial_printf("R,%.0f\r\n", duty * 100);
}

/* ------------------------------------------------------------------ */
int main(void)
{
    board_init();
    motor_set_raw(0.0f);
    serial_start();

    serial_printf("\r\n=== Aeropendulo NUCLEO-L476RG ===\r\n");
    imu_ok = imu_init();
    if (imu_ok) {
        serial_printf("IMU %s found at 0x%02X, calibrating gyro (keep still)...\r\n",
                      imu_name(), imu_address());
        imu_calibrate_gyro(500);
        imu_read(&raw);
        imu_angle_reset(&ang, &raw);
    } else {
        serial_printf("IMU NOT FOUND - check wiring (SDA D14, SCL D15, 3V3, GND), then 'scan'\r\n");
    }
    print_help();

    const float dt = LOOP_PERIOD_MS / 1000.0f;
    uint32_t next = HAL_GetTick();
    uint32_t loops = 0;
    char cmd[64];

    while (1) {
        /* commands are handled between control periods */
        if (serial_get_line(cmd, sizeof cmd))
            handle_command(cmd);

        /* fixed-rate loop */
        if ((int32_t)(HAL_GetTick() - next) < 0)
            continue;
        next += LOOP_PERIOD_MS;
        loops++;

        if (imu_ok) {
            if (imu_read(&raw)) {
                imu_angle_update(&ang, &raw, dt);
            } else {
                imu_errors++;
                if (mode == MODE_RUN) {
                    stop_all();
                    serial_printf("IMU read error: motor off\r\n");
                }
            }
        }

        button_update();

        switch (mode) {
        case MODE_RUN:
            if (fabsf(ang.theta - 90.0f) > FALL_LIMIT_DEG) {
                stop_all();
                serial_printf("FALL detected (theta %.1f): motor off\r\n", ang.theta);
                break;
            }
            motor_set(pid_step(&pid, ang.theta, ang.rate, dt));
            break;
        case MODE_RAMP:
            ramp_update();
            break;
        default:
            break;
        }

        /* telemetry */
        if (mode == MODE_IMU && loops % 10 == 0) {
            serial_try_printf("I,%.3f,%.3f,%.3f,%.1f,%.1f,%.1f,%.2f,%.2f,%.2f\r\n",
                              raw.acc[0], raw.acc[1], raw.acc[2],
                              raw.gyro[0], raw.gyro[1], raw.gyro[2],
                              ang.theta_acc, ang.theta_gyro, ang.theta);
        } else if (mode != MODE_IDLE && mode != MODE_IMU && loops % TELEMETRY_DIV == 0) {
            serial_try_printf("D,%lu,%.2f,%.2f,%.3f,%.3f,%.3f,%.2f,%.1f\r\n",
                              (unsigned long)HAL_GetTick(), ang.theta, pid.ref, pid.u,
                              pid.i, motor_duty(), ang.theta_acc, ang.rate);
        }

        /* heartbeat: slow blink idle, fast blink running */
        if (loops % ((mode == MODE_RUN) ? 20 : 100) == 0)
            HAL_GPIO_TogglePin(GPIOA, GPIO_PIN_5);
    }
}
