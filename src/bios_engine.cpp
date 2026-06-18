#include <iostream>
#include <cstdint>

#ifdef _WIN32
    #include <windows.h>
    #define EXPORT __declspec(dllexport)
#else
    #include <fstream>
    #define EXPORT __attribute__((visibility("default")))
#endif

struct AsusBiosMemoryMap {
    char cpuModel[64] = "Detecting...";
    uint32_t ramSpeedMhz = 4800;
    uint32_t totalMemoryMb = 0;
    float cpuTemperatureC = 0.0f;
    float cpuCoreVoltageV = 0.000f;
    uint8_t aiOverclockMode = 0;   
    uint8_t xmpProfileStatus = 0;  
    uint8_t intelRstEnabled = 1;   
    uint16_t bootPrioritySequence[3] = {1, 2, 3}; 
    uint32_t manualFanCurvePoints[4] = {20, 40, 70, 100}; 
    uint32_t bclkFrequency = 100;
    uint32_t cpuRatio = 54;
    uint8_t secureBootState = 1;
    uint8_t hyperThreadingState = 1;
    uint8_t virtualizationState = 1;
};

AsusBiosMemoryMap currentSystemState;

void UpdateHardwareSensors() {
#ifdef _WIN32
    currentSystemState.cpuTemperatureC = 42.5f; 
    currentSystemState.cpuCoreVoltageV = 1.25f;
#else
    std::ifstream tempFile("/sys/class/thermal/thermal_zone0/temp");
    if (tempFile.is_open()) {
        float temp;
        tempFile >> temp;
        currentSystemState.cpuTemperatureC = temp / 1000.0f;
    }
    currentSystemState.cpuCoreVoltageV = 1.25f;
#endif
}

extern "C" {
    EXPORT void* GetSystemStateAddress() {
        UpdateHardwareSensors();
        return &currentSystemState;
    }

    EXPORT bool CommitChangesToHardwareNVRAM() {
        return true; 
    }

    EXPORT void ForceSystemHardwareReboot() {
#ifdef _WIN32
        ExitWindowsEx(EWX_REBOOT, SHTDN_REASON_MAJOR_HARDWARE);
#else
        system("sudo reboot");
#endif
    }
}
