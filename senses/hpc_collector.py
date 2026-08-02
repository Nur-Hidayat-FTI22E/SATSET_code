import subprocess
import psutil
import re

class HPCCollector:
    def __init__(self, attack_mode=False):
        self.attack_mode = attack_mode

    def set_attack_mode(self, active: bool):
        self.attack_mode = active

    def read(self):
        cmd = ["perf", "stat", "-e", "cache-misses,instructions,branch-misses", "-a", "sleep", "1"]
        result = subprocess.run(cmd, capture_output=True, text=True)

        hpc_data = {
            "cache_misses": 0.0,
            "instructions_retired": 0.0,
            "branch_misses": 0.0,
            "cpu_usage": psutil.cpu_percent(interval=None)
        }

        for line in result.stderr.splitlines():
            if "cache-misses" in line:
                match = re.search(r"([\d\,]+)\s+cache-misses", line)
                if match:
                    hpc_data["cache_misses"] = float(match.group(1).replace(",", ""))
            elif "instructions" in line:
                match = re.search(r"([\d\,]+)\s+instructions", line)
                if match:
                    hpc_data["instructions_retired"] = float(match.group(1).replace(",", ""))
            elif "branch-misses" in line:
                match = re.search(r"([\d\,]+)\s+branch-misses", line)
                if match:
                    hpc_data["branch_misses"] = float(match.group(1).replace(",", ""))

        return hpc_data 
