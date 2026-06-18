#include <iostream>
#include <string>
#include <cstdint>

#ifdef _WIN32
#include <windows.h>
#define EXPORT __declspec(dllexport)
const wchar_t* UEFI_GLOBAL_GUID = L"{8BE4DF61-93CA-11D2-AA0D-00E098032B8C}";
#else
#include <cstdlib>
#define EXPORT __attribute__((visibility("default")))
#endif

struct AsusBiosMemoryMap {
    char cpuModel[64] = "Detecting...";
    uint32_t ramSpeedMhz = 0;
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
};

AsusBiosMemoryMap currentSystemState;

extern "C" {
    EXPORT void* GetSystemStateAddress() {
        return &currentSystemState;
    }

    EXPORT bool CommitChangesToHardwareNVRAM() {
#ifdef _WIN32
        BOOL success = SetFirmwareEnvironmentVariableW(
            L"AsusBiosConfigData",
            UEFI_GLOBAL_GUID,
            &currentSystemState,
            sizeof(AsusBiosMemoryMap)
        );
        return success != 0;
#else
        return true; 
#endif
    }

    EXPORT void ForceSystemHardwareReboot() {
#ifdef _WIN32
        ExitWindowsEx(EWX_REBOOT, SHTDN_REASON_MAJOR_HARDWARE | SHTDN_REASON_MINOR_MAINTENANCE);
#else
        system("sudo reboot");
#endif
    }
}
