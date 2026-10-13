"""Read-only UTM telemetry reader for the simulator or a documented serial stream."""

import argparse
import logging
import os
import sys
import threading
import time
from typing import Any, Dict, Optional

import requests

from edge.cache_buffer import OfflineCacheBuffer
from edge.virtual_utm import MATERIAL_PRESETS, VirtualUTMMachine

try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    serial = None
    SERIAL_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [EdgeAgent] %(message)s")
logger = logging.getLogger("EdgeAgent")


class EdgeAgent:
    """Read telemetry only; this agent never sends actuator or motion commands."""

    def __init__(
        self,
        port: str = "COM3",
        baud_rate: int = 9600,
        data_bits: int = 8,
        parity: str = "N",
        stop_bits: int = 1,
        timeout_sec: float = 1.0,
        polling_hz: float = 25.0,
        cloud_api_url: str = "http://127.0.0.1:8000/api/telemetry",
        sample_id: str = "TEST_SAMPLE_001",
        use_virtual: bool = True,
        virtual_material: str = "IS_1786_FE500",
        device_token: Optional[str] = None,
    ):
        self.port = port
        self.baud_rate = baud_rate
        self.data_bits = data_bits
        self.parity = parity
        self.stop_bits = stop_bits
        self.timeout_sec = timeout_sec
        self.polling_hz = max(10.0, min(50.0, float(polling_hz)))
        self.poll_interval_sec = 1.0 / self.polling_hz
        self.cloud_api_url = cloud_api_url
        self.sample_id = sample_id.strip()
        self.use_virtual = use_virtual
        self.device_token = device_token or os.getenv("UTM_DEVICE_TOKEN")
        self.optoelectronic_isolation_verified = None
        self.ftdi_hardware_signature = None
        self.is_connected = False
        self.is_running = False
        self.serial_handle = None
        self._thread: Optional[threading.Thread] = None
        self._flush_thread: Optional[threading.Thread] = None
        self.cache_buffer = OfflineCacheBuffer("edge_offline_cache.db")
        self.virtual_machine = VirtualUTMMachine(
            material_key=virtual_material,
            a_0=50.0,
            l_0=50.0,
            test_speed_mm_min=12.0,
        )

    def connect_serial(self) -> bool:
        if self.use_virtual:
            self.is_connected = True
            logger.info("Virtual simulator selected explicitly; no physical machine is connected.")
            return True
        if not SERIAL_AVAILABLE:
            self.is_connected = False
            logger.error("pyserial is unavailable; refusing simulated fallback.")
            return False
        try:
            parity_values = {"N": serial.PARITY_NONE, "E": serial.PARITY_EVEN, "O": serial.PARITY_ODD}
            self.serial_handle = serial.Serial(
                port=self.port,
                baudrate=self.baud_rate,
                bytesize=serial.EIGHTBITS if self.data_bits == 8 else self.data_bits,
                parity=parity_values.get(self.parity, serial.PARITY_NONE),
                stopbits=serial.STOPBITS_ONE if self.stop_bits == 1 else self.stop_bits,
                timeout=self.timeout_sec,
            )
            self.is_connected = True
            logger.info("Read-only serial telemetry opened on %s; no actuator writes are supported.", self.port)
            return True
        except Exception as error:
            self.is_connected = False
            logger.error("Could not open serial port %s: %s", self.port, error)
            return False

    def parse_raw_line(self, raw_line: str) -> Optional[Dict[str, Any]]:
        try:
            parts = raw_line.strip().split(",")
            if len(parts) != 3:
                if parts and parts[0]:
                    logger.warning("Malformed frame; expected exactly time_sec,force_n,displacement_mm")
                return None
            time_sec, force_n, displacement_mm = (float(part.strip()) for part in parts)
            return {
                "sample_id": self.sample_id,
                "time_sec": round(time_sec, 4),
                "force_n": round(force_n, 2),
                "displacement_mm": round(displacement_mm, 4),
            }
        except (ValueError, UnicodeDecodeError):
            logger.warning("Could not parse serial frame %r", raw_line)
            return None

    def _auth_headers(self) -> Dict[str, str]:
        if not self.device_token:
            return {}
        return {"Authorization": f"Bearer {self.device_token}"}

    def post_telemetry_to_cloud(self, packet: Dict[str, Any]) -> bool:
        try:
            response = requests.post(self.cloud_api_url, json=packet, headers=self._auth_headers(), timeout=0.8)
            if response.status_code == 200:
                return True
            if response.status_code in {400, 401, 403, 409, 422}:
                logger.error("Telemetry rejected with HTTP %s; invalid or stale frames are not queued.", response.status_code)
                return False
            self.cache_buffer.push(packet)
        except requests.RequestException:
            self.cache_buffer.push(packet)
        return False

    def _flush_offline_cache(self) -> None:
        while self.is_running:
            time.sleep(2.0)
            packets = self.cache_buffer.peek(limit=50)
            if not packets:
                continue
            batch = [{key: packet[key] for key in ("sample_id", "time_sec", "force_n", "displacement_mm")} for packet in packets]
            try:
                response = requests.post(
                    f"{self.cloud_api_url}/batch",
                    json=batch,
                    headers=self._auth_headers(),
                    timeout=2.0,
                )
                if response.status_code == 200:
                    self.cache_buffer.remove_ids([packet["id"] for packet in packets])
                elif response.status_code in {400, 401, 403, 409, 422}:
                    logger.error("Cached telemetry rejected with HTTP %s; preserving queue for operator review.", response.status_code)
                    return
            except requests.RequestException as error:
                logger.debug("Cache flush failed: %s", error)

    def start_acquisition(self) -> bool:
        if self.is_running:
            return True
        if not self.is_connected:
            logger.error("No confirmed data source connection; acquisition not started.")
            return False
        if not self.use_virtual and not self.sample_id:
            logger.error("Serial ingestion requires the active dashboard sample ID.")
            return False
        if not self.use_virtual and not self.device_token:
            logger.error("Serial ingestion requires UTM_DEVICE_TOKEN.")
            return False
        if self.use_virtual:
            self.virtual_machine.start()
        self.is_running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self._flush_thread = threading.Thread(target=self._flush_offline_cache, daemon=True)
        self._flush_thread.start()
        return True

    def stop_acquisition(self) -> None:
        self.is_running = False
        if self.use_virtual:
            self.virtual_machine.stop()
        if self.serial_handle and self.serial_handle.is_open:
            self.serial_handle.close()
        self.is_connected = False

    def tare(self) -> None:
        if self.use_virtual:
            self.virtual_machine.tare()
            logger.info("Virtual simulator tared.")
        else:
            logger.warning("Physical tare is not implemented; use the UTM controller's verified tare control.")

    def _run_loop(self) -> None:
        while self.is_running:
            loop_started = time.monotonic()
            try:
                if self.use_virtual:
                    raw_line = self.virtual_machine.generate_serial_line(self.poll_interval_sec)
                else:
                    if not self.serial_handle or not self.serial_handle.is_open:
                        self.is_connected = False
                        if not self.connect_serial():
                            time.sleep(1.0)
                            continue
                    raw_line = self.serial_handle.readline().decode("utf-8", errors="replace")
                packet = self.parse_raw_line(raw_line)
                if packet:
                    self.post_telemetry_to_cloud(packet)
            except Exception as error:
                logger.error("Telemetry read failed: %s", error)
                if not self.use_virtual:
                    self.is_connected = False
            time.sleep(max(0.001, self.poll_interval_sec - (time.monotonic() - loop_started)))


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only UTM telemetry agent; no motion control")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--virtual", action="store_true", help="Use the software simulator")
    source.add_argument("--serial", action="store_true", help="Read only from a serial telemetry stream")
    parser.add_argument("--port", default=os.getenv("UTM_SERIAL_PORT", "COM3"))
    parser.add_argument("--sample-id", default="")
    parser.add_argument("--polling-hz", type=float, default=25.0)
    parser.add_argument("--cloud-api-url", default="http://127.0.0.1:8000/api/telemetry")
    args = parser.parse_args()
    if args.serial and not args.sample_id.strip():
        parser.error("--sample-id must match a test started in the dashboard")
    agent = EdgeAgent(
        port=args.port,
        sample_id=args.sample_id,
        polling_hz=args.polling_hz,
        cloud_api_url=args.cloud_api_url,
        use_virtual=args.virtual,
    )
    if not agent.connect_serial() or not agent.start_acquisition():
        return 2
    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        agent.stop_acquisition()
    return 0


if __name__ == "__main__":
    sys.exit(main())