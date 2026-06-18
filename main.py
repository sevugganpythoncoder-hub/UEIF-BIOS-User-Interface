import sys
import os
import random
import platform
import ctypes
import psutil
import socket
import subprocess  
from datetime import datetime
import customtkinter as ctk

class AdvancedFirmwareMemoryMap(ctypes.Structure):
    _fields_ = [
        ("cpu_model_string", ctypes.c_char * 64),
        ("ram_clock_speed_mhz", ctypes.c_uint32),
        ("total_system_memory_mb", ctypes.c_uint32),
        ("cpu_core_temperature_c", ctypes.c_float),
        ("cpu_core_voltage_v", ctypes.c_float),
        ("ai_overclock_profile_index", ctypes.c_uint8),
        ("xmp_profile_configuration", ctypes.c_uint8),
        ("intel_rst_driver_enabled", ctypes.c_uint8),
        ("boot_priority_array", ctypes.c_uint16 * 3),
        ("hardware_fan_curve_thresholds", ctypes.c_uint32 * 4),
        ("base_clock_frequency_bclk", ctypes.c_uint32),
        ("cpu_core_ratio_multiplier", ctypes.c_uint32),
        ("secure_boot_latch_state", ctypes.c_uint8),
        ("hyper_threading_state", ctypes.c_uint8),
        ("virtualization_vtx_state", ctypes.c_uint8)
    ]

try:
    system_os = platform.system()
    binary_name = "bios_engine_win_x64.dll" if system_os == "Windows" else "bios_engine_linux_x64.so"

    # 1. Resolve the path to the binary first
    path_in_bin = os.path.abspath(os.path.join(os.path.dirname(__file__), "bin", binary_name))
    path_in_root = os.path.abspath(os.path.join(os.path.dirname(__file__), binary_name))
    
    if os.path.exists(path_in_bin):
        target_path = path_in_bin
    elif os.path.exists(path_in_root):
        target_path = path_in_root
    else:
        print(f"DEBUG: Could not find {binary_name} in bin/ or root directory.")
        raise FileNotFoundError

    
    if system_os == "Windows":
        is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
        if not is_admin:
            executable = sys.executable
            arguments = " ".join([f'"{arg}"' for arg in sys.argv])
            ctypes.windll.shell32.ShellExecuteW(None, "runas", executable, arguments, None, 1)
            sys.exit(0)
            
    elif system_os == "Linux":
        if os.geteuid() != 0:
            print("[INFO] Root privileges required. Re-launching application via sudo wrapper...")
            try:
                subprocess.check_call(["sudo", sys.executable] + sys.argv)
            except subprocess.CalledProcessError as e:
                print(f"[ERROR] Re-authentication lifecycle interrupted: {e}")
                sys.exit(1)
            sys.exit(0)

    
    if system_os == "Windows":
        cpp_firmware_library = ctypes.CDLL(target_path, winmode=0)
    else:
        cpp_firmware_library = ctypes.CDLL(target_path)

    cpp_firmware_library.GetSystemStateAddress.restype = ctypes.POINTER(AdvancedFirmwareMemoryMap)
    shared_firmware_state = cpp_firmware_library.GetSystemStateAddress().contents
    IS_NATIVE_RUNTIME_ACTIVE = True
        
except Exception as e:
    shared_firmware_state = AdvancedFirmwareMemoryMap()
    IS_NATIVE_RUNTIME_ACTIVE = False
    print(f"\n[!] DLL LOAD ERROR: {e}")  
    import traceback; traceback.print_exc()

def poll_operating_system_hardware_specs():
    try:
        import winreg
        registry_handle = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
        resolved_cpu_string = winreg.QueryValueEx(registry_handle, "ProcessorNameString")[0].strip()
        winreg.CloseKey(registry_handle)
    except Exception:
        resolved_cpu_string = platform.processor()
    
    shared_firmware_state.cpu_model_string = resolved_cpu_string.encode('utf-8')[:63]
    shared_firmware_state.total_system_memory_mb = int(psutil.virtual_memory().total / (1024 * 1024))
    shared_firmware_state.ram_clock_speed_mhz = 4800
    shared_firmware_state.hyper_threading_state = 1
    shared_firmware_state.virtualization_vtx_state = 1

def discover_gpu_hardware():
    try:
        import winreg
        path = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}"
        base_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path)
        for i in range(10):
            try:
                sub_key_name = f"{i:04d}"
                sub_key = winreg.OpenKey(base_key, sub_key_name)
                gpu_name, _ = winreg.QueryValueEx(sub_key, "DriverDesc")
                winreg.CloseKey(sub_key)
                winreg.CloseKey(base_key)
                return str(gpu_name)
            except Exception:
                continue
        winreg.CloseKey(base_key)
    except Exception:
        pass
    return "Standard Graphics Adapter"

def gather_network_configuration():
    interfaces = psutil.net_if_addrs()
    gateways = psutil.net_if_stats()
    active_adapter = "None"
    ip_address = "0.0.0.0"
    netmask = "0.0.0.0"
    config_type = "Static / Unknown"

    for interface_name, addresses in interfaces.items():
        if interface_name in gateways and gateways[interface_name].isup:
            if "loopback" in interface_name.lower() or "vbox" in interface_name.lower() or "vmware" in interface_name.lower():
                continue
            active_adapter = interface_name
            for addr in addresses:
                if addr.family == socket.AF_INET:
                    ip_address = addr.address
                    netmask = addr.netmask
                    break
            break

    try:
        if platform.system() == "Windows":
            output = subprocess.check_output("ipconfig /all", shell=True).decode('ansi')
            adapter_found = False
            for line in output.split('\n'):
                if active_adapter in line or (("adapter" in line.lower() or "wi-fi" in line.lower() or "ethernet" in line.lower()) and ":" in line):
                    adapter_found = True
                if adapter_found and "dhcp enabled" in line.lower():
                    if "yes" in line.lower():
                        config_type = "DHCP Automatically Assigned"
                    else:
                        config_type = "Manually Configured (Static)"
                    break
        elif platform.system() == "Linux":
            route_output = subprocess.check_output("ip route", shell=True).decode('utf-8')
            if "dhcp" in route_output.lower():
                config_type = "DHCP Automatically Assigned"
            else:
                config_type = "Manually Configured (Static)"
    except Exception:
        pass

    return active_adapter, ip_address, netmask, config_type

poll_operating_system_hardware_specs()
ctk.set_appearance_mode("dark")

class PycEzAudiitDashboard(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("PyC BIOS Utility")
        self.geometry("1240x840")
        self.configure(fg_color="#0b0e11") 
        
        self.active_interface_mode = "EZ"
        self.execution_lifecycle_active = True
        self.hardware_boot_targets = {1: "Windows Boot Manager (M.2 NVMe)", 2: "Ubuntu Linux (SATA SSD)", 3: "USB Drive"}
        self.detected_gpu = discover_gpu_hardware()

        self.grid_rowconfigure(0, weight=1)   
        self.grid_rowconfigure(1, weight=12)  
        self.grid_rowconfigure(2, weight=1)   
        self.grid_columnconfigure(0, weight=1)

        self.initialize_top_navigation_bar()
        self.main_viewport_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_viewport_container.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        
        self.render_requested_layout_view()
        self.execute_sensor_telemetry_loop()
        
        self.bind("<F7>", lambda event: self.process_layout_view_toggle())
        self.bind("<F10>", lambda event: self.commit_workspace_changes_and_reboot())
        
        self.protocol("WM_DELETE_WINDOW", self.intercept_window_destruction_sequence)

    def intercept_window_destruction_sequence(self):
        self.execution_lifecycle_active = False
        self.quit()
        self.destroy()

    def initialize_top_navigation_bar(self):
        top_bar_frame = ctk.CTkFrame(self, fg_color="#141a1f", height=55, corner_radius=0)
        top_bar_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 4))
        
        ctk.CTkLabel(top_bar_frame, text="PyC", font=("Arial", 18, "bold"), text_color="#00ffff").pack(side="left", padx=(20, 10))
        self.mode_context_title = ctk.CTkLabel(top_bar_frame, text="UEFI BIOS Utility - EZ Mode", font=("Arial", 14), text_color="white")
        self.mode_context_title.pack(side="left")
        
        knockoff_watermark = ctk.CTkLabel(top_bar_frame, text="A Knockoff of Asus BIOS system", font=("Arial", 10, "italic"), text_color="#00ffff")
        knockoff_watermark.pack(side="left", padx=15)
        
        self.layout_toggle_action_button = ctk.CTkButton(top_bar_frame, text="Advanced Mode (F7)", width=140, fg_color="#222b35", hover_color="#323f4e", command=self.process_layout_view_toggle)
        self.layout_toggle_action_button.pack(side="right", padx=15)
        self.realtime_clock_display = ctk.CTkLabel(top_bar_frame, text="", font=("Consolas", 13), text_color="#a2b4c2")
        self.realtime_clock_display.pack(side="right", padx=10)
        self.sync_clock_time()

    def sync_clock_time(self):
        if not self.execution_lifecycle_active:
            return
        now = datetime.now()
        timestamp = now.strftime("%m/%d/%Y %A  %H:%M:%S")
        self.realtime_clock_display.configure(text=timestamp)
        self.after(1000, self.sync_clock_time)

    def process_layout_view_toggle(self):
        if self.active_interface_mode == "EZ":
            self.active_interface_mode = "ADVANCED"
            self.mode_context_title.configure(text="UEFI BIOS Utility - Advanced Mode")
            self.layout_toggle_action_button.configure(text="EZ Mode (F7)")
        else:
            self.active_interface_mode = "EZ"
            self.mode_context_title.configure(text="UEFI BIOS Utility - EZ Mode")
            self.layout_toggle_action_button.configure(text="Advanced Mode (F7)")
        self.render_requested_layout_view()

    def render_requested_layout_view(self):
        for child_widget in self.main_viewport_container.winfo_children():
            child_widget.destroy()

        if self.active_interface_mode == "EZ":
            self.assemble_ez_mode_workspace()
        else:
            self.assemble_advanced_mode_workspace()

    def get_os_string(self):
        return f"{platform.system()} {platform.release()} (Build {platform.version().split('.')[2]})" if platform.system() == "Windows" else f"{platform.system()} {platform.release()}"

    def assemble_ez_mode_workspace(self):
        self.main_viewport_container.grid_columnconfigure(0, weight=3)
        self.main_viewport_container.grid_columnconfigure(1, weight=1)
        self.main_viewport_container.grid_rowconfigure(0, weight=1)

        left_side_panel_stack = ctk.CTkFrame(self.main_viewport_container, fg_color="transparent")
        left_side_panel_stack.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        left_side_panel_stack.grid_columnconfigure(0, weight=1)
        left_side_panel_stack.grid_rowconfigure(0, weight=1)
        left_side_panel_stack.grid_rowconfigure(1, weight=2)

        telemetry_card_box = ctk.CTkFrame(left_side_panel_stack, fg_color="#11161b", border_color="#1f2933", border_width=1)
        telemetry_card_box.grid(row=0, column=0, sticky="nsew", pady=4)
        telemetry_card_box.grid_columnconfigure(0, weight=2)
        telemetry_card_box.grid_columnconfigure(1, weight=1)

        adapter, ip, mask, net_type = gather_network_configuration()

        formatted_specs_string = (
            f"Information:\n"
            f"OS Profile: {self.get_os_string()}\n"
            f"GPU Hardware: {self.detected_gpu}\n"
            f"Net Adapter: {adapter}\n"
            f"IP Address: {ip}  |  Mask: {mask}\n"
            f"Net Assignment: {net_type}\n"
            f"CPU Hardware: {shared_firmware_state.cpu_model_string.decode('utf-8')}\n"
            f"Total System RAM: {shared_firmware_state.total_system_memory_mb} MB"
        )
        ctk.CTkLabel(telemetry_card_box, text=formatted_specs_string, font=("Consolas", 11), justify="left", anchor="w").grid(row=0, column=0, padx=15, pady=10, sticky="w")
        
        self.live_telemetry_label_handle = ctk.CTkLabel(telemetry_card_box, text="CPU Temp: --°C\nVoltage: -.-- V", font=("Consolas", 12, "bold"), text_color="#00ffff")
        self.live_telemetry_label_handle.grid(row=0, column=1, padx=15, pady=10, sticky="e")

        system_components_card = ctk.CTkFrame(left_side_panel_stack, fg_color="#11161b", border_color="#1f2933", border_width=1)
        system_components_card.grid(row=1, column=0, sticky="nsew", pady=4)
        
        ctk.CTkLabel(system_components_card, text="DRAM & Active Fan Status", font=("Arial", 12, "bold"), text_color="#00ffff").pack(anchor="w", padx=15, pady=5)
        ctk.CTkLabel(system_components_card, text=f"DIMM_A1: Hardware Bus Module Speed {shared_firmware_state.ram_clock_speed_mhz}MHz", font=("Consolas", 11)).pack(anchor="w", padx=25)
        
        self.fan_telemetry_label = ctk.CTkLabel(system_components_card, text="CPU Fan Speed: 0 RPM\nGPU Speed: 0 MHz", font=("Consolas", 11), justify="left", anchor="w")
        self.fan_telemetry_label.pack(anchor="w", padx=25, pady=5)

        ctk.CTkLabel(system_components_card, text="Intel Rapid Storage Technology", font=("Arial", 12, "bold"), text_color="#00ffff").pack(anchor="w", padx=15, pady=(10, 2))
        self.intel_rst_interactive_switch = ctk.CTkSwitch(system_components_card, text="RST Mode Driver Configuration Status", command=self.synchronize_rst_latch_to_memory)
        if shared_firmware_state.intel_rst_driver_enabled == 1: self.intel_rst_interactive_switch.select()
        self.intel_rst_interactive_switch.pack(anchor="w", padx=25, pady=5)

        ctk.CTkLabel(system_components_card, text="X.M.P. Profile Settings Selector", font=("Arial", 12, "bold"), text_color="#00ffff").pack(anchor="w", padx=15, pady=(10, 2))
        self.xmp_selection_combobox = ctk.CTkComboBox(system_components_card, values=["Disabled", "Profile #1 (4800MHz)", "Profile #2 (5200MHz)"], command=self.synchronize_xmp_state_to_memory, width=220)
        self.xmp_selection_combobox.set("Disabled" if shared_firmware_state.xmp_profile_configuration == 0 else f"Profile #{shared_firmware_state.xmp_profile_configuration}")
        self.xmp_selection_combobox.pack(anchor="w", padx=25, pady=5)

        right_side_panel_stack = ctk.CTkFrame(self.main_viewport_container, fg_color="transparent")
        right_side_panel_stack.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        right_side_panel_stack.grid_columnconfigure(0, weight=1)
        right_side_panel_stack.grid_rowconfigure(0, weight=1)
        right_side_panel_stack.grid_rowconfigure(1, weight=2)

        overclock_config_card = ctk.CTkFrame(right_side_panel_stack, fg_color="#11161b", border_color="#1f2933", border_width=1)
        overclock_config_card.grid(row=0, column=0, sticky="nsew", pady=4)
        ctk.CTkLabel(overclock_config_card, text="AI Overclocking Tuning & Power", font=("Arial", 12, "bold"), text_color="#00ffff").pack(anchor="w", padx=15, pady=5)
        
        self.battery_progress_bar = ctk.CTkProgressBar(overclock_config_card, width=180, progress_color="#27ae60")
        self.battery_progress_bar.pack(pady=(5, 2), padx=20, anchor="w")
        self.battery_status_label = ctk.CTkLabel(overclock_config_card, text="Battery: --%", font=("Consolas", 11))
        self.battery_status_label.pack(pady=(0, 5), padx=20, anchor="w")

        self.ai_tuning_profile_button = ctk.CTkButton(overclock_config_card, text="Normal Profile Mode", fg_color="#1c8adb", command=self.toggle_ai_overclock_profile)
        if shared_firmware_state.ai_overclock_profile_index == 1: self.ai_tuning_profile_button.configure(text="ASUS Optimal Performance", fg_color="#e74c3c")
        self.ai_tuning_profile_button.pack(pady=5, padx=20, fill="x")

        self.boot_priority_list_card = ctk.CTkFrame(right_side_panel_stack, fg_color="#11161b", border_color="#1f2933", border_width=1)
        self.boot_priority_list_card.grid(row=1, column=0, sticky="nsew", pady=4)
        self.rebuild_interactive_boot_priority_list()

    def assemble_advanced_mode_workspace(self):
        self.main_viewport_container.grid_columnconfigure(0, weight=1)
        self.main_viewport_container.grid_rowconfigure(0, weight=1)

        advanced_tab_view_manager = ctk.CTkTabview(self.main_viewport_container, fg_color="#11161b", segmented_button_selected_color="#00ffff")
        advanced_tab_view_manager.grid(row=0, column=0, sticky="nsew")
        
        advanced_tab_view_manager.add("Ai Tweaker")
        advanced_tab_view_manager.add("Advanced CPU")
        advanced_tab_view_manager.add("Boot Security")
        advanced_tab_view_manager.add("How-To Guide")
        advanced_tab_view_manager.add("Credits & Legal")

        ai_tweaker_tab_handle = advanced_tab_view_manager.tab("Ai Tweaker")
        bclk_row_container = ctk.CTkFrame(ai_tweaker_tab_handle, fg_color="transparent")
        bclk_row_container.pack(fill="x", pady=8, padx=10)
        ctk.CTkLabel(bclk_row_container, text="BCLK Frequency (MHz):", width=200, anchor="w").pack(side="left")
        self.bclk_value_input_field = ctk.CTkEntry(bclk_row_container, width=150)
        self.bclk_value_input_field.insert(0, str(shared_firmware_state.base_clock_frequency_bclk))
        self.bclk_value_input_field.pack(side="left")
        self.bclk_value_input_field.bind("<FocusOut>", lambda focused_out_event: self.synchronize_advanced_inputs_to_memory())

        ratio_row_container = ctk.CTkFrame(ai_tweaker_tab_handle, fg_color="transparent")
        ratio_row_container.pack(fill="x", pady=8, padx=10)
        ctk.CTkLabel(ratio_row_container, text="CPU Core Ratio:", width=200, anchor="w").pack(side="left")
        self.cpu_ratio_input_field = ctk.CTkEntry(ratio_row_container, width=150)
        self.cpu_ratio_input_field.insert(0, str(shared_firmware_state.cpu_core_ratio_multiplier))
        self.cpu_ratio_input_field.pack(side="left")
        self.cpu_ratio_input_field.bind("<FocusOut>", lambda focused_out_event: self.synchronize_advanced_inputs_to_memory())

        advanced_cpu_tab_handle = advanced_tab_view_manager.tab("Advanced CPU")
        ht_row = ctk.CTkFrame(advanced_cpu_tab_handle, fg_color="transparent")
        ht_row.pack(fill="x", pady=8, padx=10)
        ctk.CTkLabel(ht_row, text="Intel Hyper-Threading Technology:", width=250, anchor="w").pack(side="left")
        self.ht_switch = ctk.CTkSwitch(ht_row, text="Active", command=self.synchronize_advanced_inputs_to_memory)
        if shared_firmware_state.hyper_threading_state == 1: self.ht_switch.select()
        self.ht_switch.pack(side="left")

        vtx_row = ctk.CTkFrame(advanced_cpu_tab_handle, fg_color="transparent")
        vtx_row.pack(fill="x", pady=8, padx=10)
        ctk.CTkLabel(vtx_row, text="Intel Virtualization Technology (VT-x):", width=250, anchor="w").pack(side="left")
        self.vtx_switch = ctk.CTkSwitch(vtx_row, text="Active", command=self.synchronize_advanced_inputs_to_memory)
        if shared_firmware_state.virtualization_vtx_state == 1: self.vtx_switch.select()
        self.vtx_switch.pack(side="left")

        boot_security_tab_handle = advanced_tab_view_manager.tab("Boot Security")
        security_row_container = ctk.CTkFrame(boot_security_tab_handle, fg_color="transparent")
        security_row_container.pack(fill="x", pady=8, padx=10)
        ctk.CTkLabel(security_row_container, text="Secure Boot State:", width=200, anchor="w").pack(side="left")
        self.secure_boot_toggle_switch = ctk.CTkSwitch(security_row_container, text="Enabled Status", command=self.synchronize_advanced_inputs_to_memory)
        if shared_firmware_state.secure_boot_latch_state == 1: self.secure_boot_toggle_switch.select()
        self.secure_boot_toggle_switch.pack(side="left")

        guide_tab_handle = advanced_tab_view_manager.tab("How-To Guide")
        guide_textbox = ctk.CTkTextbox(guide_tab_handle, width=1100, height=350, font=("Consolas", 11))
        guide_textbox.pack(padx=10, pady=10, fill="both", expand=True)
        guide_text = (
            "yo so if u want to configure things properly check this lines:\n\n"
            "1. OVERCLOCKING RAM OR PROCESSR:\n"
            "   click over to the 'Ai Tweaker' panel. change your bclk frequency numbers or core ratio\n"
            "   multiplier manually. if u push it way to high your computer might instantly freeze\n"
            "   or get stuck looping.\n\n"
            "2. PROCESSR SPECIFFIC CHOICES:\n"
            "   the 'Advanced CPU' tab lets u flip hyper-threading or vt-x virtualisation on or off.\n"
            "   doing this could change how heavy games or android emulators run on your system.\n\n"
            "3. FIXING SYSTEM DRIVES ORDER:\n"
            "   go to the right side block layout in EZ Mode. click that up arrow sign next to your\n"
            "   main windows boot manager drive or linux drive to push it straight to top slot.\n\n"
            "4. QUITING SAFELY:\n"
            "   when u finish making changes just click the bright green 'Save & Exit' button at\n"
            "   the bottom. this closes down the interface completely and reboots right back up."
        )
        guide_textbox.insert("1.0", guide_text)
        guide_textbox.configure(state="disabled")

        legal_tab_handle = advanced_tab_view_manager.tab("Credits & Legal")
        textbox = ctk.CTkTextbox(legal_tab_handle, width=1100, height=350, font=("Consolas", 11))
        textbox.pack(padx=10, pady=10, fill="both", expand=True)
        
        legal_text = (
            "================================================================================\n"
            "                                CREDITS & LICENSE                               \n"
            "================================================================================\n\n"
            "Owner name: Kev1inmates w/h mohit\n"
            "System Based ASUS UEFI and some shyt\n\n"
            "--------------------------------------------------------------------------------\n"
            "MIT LICENSE\n"
            "--------------------------------------------------------------------------------\n"
            "Permission is hereby granted, free of charge, to any person obtaining a copy\n"
            "of this software and associated documentation files (the \"Software\"), to deal\n"
            "in the Software without restriction, including without limitation the rights\n"
            "to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n"
            "copies of the Software, and to permit persons to whom the Software is\n"
            "furnished to do so, subject to the following conditions:\n\n"
            "The above copyright notice and this permission notice shall be included in all\n"
            "copies or substantial portions of the Software.\n\n"
            "The SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\n"
            "IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\n"
            "FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\n"
            "AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\n"
            "LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\n"
            "OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE\n"
            "SOFTWARE.\n\n"
            "--------------------------------------------------------------------------------\n"
            "CRITICAL HARDWARE LIABILTY DISCLAIMER\n"
            "--------------------------------------------------------------------------------\n"
            "IF THE HOST PHYSICAL COMPUTER BECOMES UNBOOTABLE, EXPERIENCES HARDWARE CORRUPTION,\n"
            "OR SUFFERS A PERMANENT SYSTEM ENVIRONMENT BRICK EVENT, THE AUTHOR AND DEVELOPERS\n"
            "OF THIS COMPONENT UTILITY SHALL NOT BE HELD RESPONSIBLE, LIABLE, OR OBLIGATED\n"
            "FOR COMPENSATORY ACTIONS OR SYSTEM RECOVERIES UNDER ANY CLAUSE."
        )
        textbox.insert("1.0", legal_text)
        textbox.configure(state="disabled")

    def synchronize_advanced_inputs_to_memory(self):
        try: 
            if hasattr(self, 'bclk_value_input_field') and self.bclk_value_input_field.winfo_exists():
                shared_firmware_state.base_clock_frequency_bclk = int(self.bclk_value_input_field.get())
        except (ValueError, AttributeError): 
            pass
        try: 
            if hasattr(self, 'cpu_ratio_input_field') and self.cpu_ratio_input_field.winfo_exists():
                shared_firmware_state.cpu_core_ratio_multiplier = int(self.cpu_ratio_input_field.get())
        except (ValueError, AttributeError): 
            pass
        if hasattr(self, 'secure_boot_toggle_switch') and self.secure_boot_toggle_switch.winfo_exists():
            shared_firmware_state.secure_boot_latch_state = 1 if self.secure_boot_toggle_switch.get() else 0
        if hasattr(self, 'ht_switch') and self.ht_switch.winfo_exists():
            shared_firmware_state.hyper_threading_state = 1 if self.ht_switch.get() else 0
        if hasattr(self, 'vtx_switch') and self.vtx_switch.winfo_exists():
            shared_firmware_state.virtualization_vtx_state = 1 if self.vtx_switch.get() else 0

    def rebuild_interactive_boot_priority_list(self):
        for active_child in self.boot_priority_list_card.winfo_children():
            active_child.destroy()

        ctk.CTkLabel(self.boot_priority_list_card, text="Boot Priority Sequence List", font=("Arial", 12, "bold"), text_color="#00ffff").pack(anchor="w", padx=15, pady=5)
        
        for priority_index, assigned_device_id in enumerate(shared_firmware_state.boot_priority_array):
            list_item_frame = ctk.CTkFrame(self.boot_priority_list_card, fg_color="#182026", height=38)
            list_item_frame.pack(fill="x", padx=12, pady=4)
            resolved_device_string = self.hardware_boot_targets.get(assigned_device_id, "Unknown Drive Device Connection")
            ctk.CTkLabel(list_item_frame, text=f"P{priority_index+1}: {resolved_device_string[:24]}...", font=("Consolas", 11)).pack(side="left", padx=10, pady=5)
            if priority_index > 0:
                ctk.CTkButton(list_item_frame, text="UP", width=24, height=22, fg_color="#2b3b4c", 
                               command=lambda index_to_shift=priority_index: self.execute_boot_array_swap_routine(index_to_shift)).pack(side="right", padx=5)

    def execute_boot_array_swap_routine(self, array_index):
        temporary_value_latch = shared_firmware_state.boot_priority_array[array_index]
        shared_firmware_state.boot_priority_array[array_index] = shared_firmware_state.boot_priority_array[array_index - 1]
        shared_firmware_state.boot_priority_array[array_index - 1] = temporary_value_latch
        self.rebuild_interactive_boot_priority_list()

    def synchronize_rst_latch_to_memory(self):
        shared_firmware_state.intel_rst_driver_enabled = 1 if self.intel_rst_interactive_switch.get() else 0

    def synchronize_xmp_state_to_memory(self, user_combobox_choice):
        if "Disabled" in user_combobox_choice: 
            shared_firmware_state.xmp_profile_configuration = 0
        elif "#1" in user_combobox_choice: 
            shared_firmware_state.xmp_profile_configuration = 1
        elif "#2" in user_combobox_choice: 
            shared_firmware_state.xmp_profile_configuration = 2

    def toggle_ai_overclock_profile(self):
        if shared_firmware_state.ai_overclock_profile_index == 0:
            shared_firmware_state.ai_overclock_profile_index = 1
            self.ai_tuning_profile_button.configure(text="ASUS Optimal Performance", fg_color="#e74c3c")
        else:
            shared_firmware_state.ai_overclock_profile_index = 0
            self.ai_tuning_profile_button.configure(text="Normal Profile Mode", fg_color="#1c8adb")

    def draw_bottom_utility_actions_bar(self):
        bottom_actions_frame = ctk.CTkFrame(self, fg_color="#141a1f", height=50, corner_radius=0)
        bottom_actions_frame.grid(row=2, column=0, sticky="nsew", pady=(4, 0))
        
        status_string_output = "Connected: C++ Native Runtime Engine DLL Active" if IS_NATIVE_RUNTIME_ACTIVE else "Running in Python Simulation Emulation Sandbox Mode"
        ctk.CTkLabel(bottom_actions_frame, text=status_string_output, font=("Arial", 11, "italic"), text_color="#7f8c8d").pack(side="left", padx=20)
        ctk.CTkButton(bottom_actions_frame, text="Save & Exit", fg_color="#27ae60", hover_color="#2ecc71", command=self.commit_workspace_changes_and_reboot).pack(side="right", padx=20)

    def commit_workspace_changes_and_reboot(self):
        self.synchronize_advanced_inputs_to_memory()
        if IS_NATIVE_RUNTIME_ACTIVE:
            try:
                is_nvram_commit_successful = cpp_firmware_library.CommitChangesToHardwareNVRAM()
                if is_nvram_commit_successful:
                    cpp_firmware_library.ForceSystemHardwareReboot()
            except Exception:
                pass
        self.intercept_window_destruction_sequence()

    def execute_sensor_telemetry_loop(self):
        if not self.execution_lifecycle_active:
            return
        
        shared_firmware_state.cpu_core_temperature_c = round(random.uniform(30.5, 33.5))
        shared_firmware_state.cpu_core_voltage_v = round(random.uniform(1.024, 1.048), 2)
        
        simulated_fan_rpm = int(random.uniform(1200, 1450))
        simulated_gpu_mhz = int(random.uniform(2100, 2450))
        
        battery_data = psutil.sensors_battery()
        if battery_data:
            pct = battery_data.percent
            status_text = f"Battery: {int(pct)}%"
            val = pct / 100.0
        else:
            status_text = "Battery: N/A (Desktop)"
            val = 1.0

        if self.active_interface_mode == "EZ":
            if hasattr(self, 'live_telemetry_label_handle') and self.live_telemetry_label_handle.winfo_exists():
                self.live_telemetry_label_handle.configure(text=f"CPU Temp: {int(shared_firmware_state.cpu_core_temperature_c)}°C\nVoltage: {shared_firmware_state.cpu_core_voltage_v:.2f} V")
            if hasattr(self, 'fan_telemetry_label') and self.fan_telemetry_label.winfo_exists():
                self.fan_telemetry_label.configure(text=f"CPU Fan Speed: {simulated_fan_rpm} RPM\nGPU Core Speed: {simulated_gpu_mhz} MHz")
            if hasattr(self, 'battery_status_label') and self.battery_status_label.winfo_exists():
                self.battery_status_label.configure(text=status_text)
                self.battery_progress_bar.set(val)
        
        self.after(750, self.execute_sensor_telemetry_loop)

if __name__ == "__main__":
    firmware_application_instance = PycEzAudiitDashboard()
    firmware_application_instance.draw_bottom_utility_actions_bar()
    firmware_application_instance.mainloop()
