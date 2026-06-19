#include <iostream>
#include <cstdint>

#ifdef _WIN32
    #include <windows.h>
    #define EXPORT __declspec(dllexport)
    const wchar_t* UEFI_GLOBAL_GUID = L"{8BE4DF61-93CA-11D2-AA0D-00E098032B8C}";
#else
    #include <fstream>
    #include <cstdlib>
    #include <unistd.h>
    #define EXPORT __attribute__((visibility("default")))
#endif

struct AsusBiosMemoryMap {
    char cpuModel[64] = "Detecting Hardware...";
    uint32_t ramSpeedMhz = 4800;
    uint32_t totalMemoryMb = 16384;
    float cpuTemperatureC = 45.0f;
    float cpuCoreVoltageV = 1.220f;
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

#ifdef _WIN32
bool EnableFirmwarePrivilege() {
    HANDLE hToken;
    TOKEN_PRIVILEGES tkp;

    if (!OpenProcessToken(GetCurrentProcess(), TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY, &hToken)) {
        return false;
    }

    if (!LookupPrivilegeValue(NULL, SE_SYSTEM_ENVIRONMENT_NAME, &tkp.Privileges[0].Luid)) {
        CloseHandle(hToken);
        return false;
    }

    tkp.PrivilegeCount = 1;
    tkp.Privileges[0].Attributes = SE_PRIVILEGE_ENABLED;

    if (!AdjustTokenPrivileges(hToken, FALSE, &tkp, sizeof(TOKEN_PRIVILEGES), NULL, NULL)) {
        CloseHandle(hToken);
        return false;
    }

    bool success = (GetLastError() == ERROR_SUCCESS);
    CloseHandle(hToken);
    return success;
}
#endif

extern "C" {
    EXPORT void* GetSystemStateAddress() {
        return &currentSystemState;
    }

    EXPORT bool CommitChangesToHardwareNVRAM() {
#ifdef _WIN32
        if (!EnableFirmwarePrivilege()) {
            std::cerr << "[ERROR] Target token execution privilege missing." << std::endl;
            return false;
        }

        BOOL success = SetFirmwareEnvironmentVariableW(
            L"AsusBiosConfigData",
            UEFI_GLOBAL_GUID,
            &currentSystemState,
            sizeof(AsusBiosMemoryMap)
        );
        return success != 0;
#else
        const char* efi_path = "/sys/firmware/efi/efivars/AsusBiosConfigData-8be4df61-93ca-11d2-aa0d-00e098032b8c";
        std::ofstream file(efi_path, std::ios::binary);
        if (!file.is_open()) {
            std::cerr << "[ERROR] Writing runtime variables to efivarfs failed." << std::endl;
            return false;
        }

        uint32_t efi_attributes = 0x00000007;
        file.write(reinterpret_cast<const char*>(&efi_attributes), sizeof(efi_attributes));
        file.write(reinterpret_cast<const char*>(&currentSystemState), sizeof(AsusBiosMemoryMap));
        file.close();
        return true;
#endif
    }

    EXPORT void ForceSystemHardwareReboot() {
#ifdef _WIN32
        ExitWindowsEx(EWX_REBOOT, SHTDN_REASON_MAJOR_HARDWARE);
#else
        if (system("reboot") != 0) {
            std::cerr << "[ERROR] Execution of reboot environment utility dropped." << std::endl;
        }
#endif
    }
}
