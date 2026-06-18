#include <iostream>
#include <cstdint>
#include <cstring>

#ifdef _WIN32
    #include <windows.h>
    #define EXPORT __declspec(dllexport)
#else
    #include <fstream>
    #define EXPORT __attribute__((visibility("default")))
#endif

struct AsusBiosMemoryMap {
    char cpuModel[64];
    uint32_t ramSpeedMhz;
    uint32_t totalMemoryMb;
    float cpuTemperatureC;
    float cpuCoreVoltageV;
    uint8_t aiOverclockMode;   
    uint8_t xmpProfileStatus;  
    uint8_t intelRstEnabled;   
    uint16_t bootPrioritySequence[3]; 
    uint32_t manualFanCurvePoints[4]; 
    uint32_t bclkFrequency;
    uint32_t cpuRatio;
    uint8_t secureBootState;
    uint8_t hyperThreadingState;
    uint8_t virtualizationState;
};


AsusBiosMemoryMap currentSystemState;

extern "C" {
    EXPORT void* GetSystemStateAddress() {
        return &currentSystemState;
    }

    EXPORT bool CommitChangesToHardwareNVRAM() {
        
        
        std::cout << "Committing BIOS Settings..." << std::endl;
        std::cout << "Target BCLK: " << currentSystemState.bclkFrequency << std::endl;
        std::cout << "CPU Ratio: " << currentSystemState.cpuRatio << std::endl;
        std::cout << "Secure Boot: " << (int)currentSystemState.secureBootState << std::endl;

#ifdef _WIN32
        return true; 
#else
        return true; 
#endif
    }

    EXPORT void ForceSystemHardwareReboot() {
#ifdef _WIN32
        ExitWindowsEx(EWX_REBOOT, SHTDN_REASON_MAJOR_HARDWARE);
#else
        system("sudo reboot");
#endif
    }
}
