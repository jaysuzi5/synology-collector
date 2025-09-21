import requests
import os
import traceback
from synology_dsm import SynologyDSM
from dotenv import load_dotenv
from jTookkit.jLogging import LoggingInfo, Logger, EventType
from jTookkit.jConfig import Config

class SynologyCollector:
    def __init__(self, config):
        self._config = config
        logging_info = LoggingInfo(**self._config.get("logging_info", {}))
        self._logger = Logger(logging_info)
        self._local_api_base_url = os.getenv("LOCAL_API_BASE_URL").strip()
        self._synology_user = os.getenv("NAS_USER").strip()
        self._synology_password = os.getenv("NAS_PASSWORD").strip()
        self._synology_ip = os.getenv("NAS_IP").strip()
        self._synology_port = int(os.getenv("NAS_PORT").strip())
        self._transaction = None

    def process(self):
        payload = {}
        self._transaction = self._logger.transaction_event(EventType.TRANSACTION_START)
        payload['return_code'] = 200

        data = self._get_metrics(payload)

        if payload['return_code'] == 200:
            self._load_data(data, payload)
        else:
            payload['message'] = 'Issue collecting Synology stats'
            payload['return_code'] = 500

        return_code = payload['return_code']
        payload.pop('return_code')
        if return_code != 200 and "message" not in payload:
            payload['message'] = 'Issue inserting Synology stats'
        self._logger.transaction_event(EventType.TRANSACTION_END, transaction=self._transaction,
                                       payload=payload, return_code=return_code)

    def _get_metrics(self, payload):
        """
        Connect to the Synology NAS and return a structured dictionary with
        system info, CPU/memory usage, network stats, and storage info.
        """
        payload['return_code'] = 200
        response = {}
        source_transaction = self._logger.transaction_event(EventType.SPAN_START, payload=payload,
                                                            source_component="synology: Collect Data",
                                                            transaction=self._transaction)
        try:
            synology = SynologyDSM(self._synology_ip, self._synology_port, self._synology_user,
                              self._synology_password, use_https=False)

            # Update all info
            synology.information.update()
            synology.utilisation.update()
            synology.storage.update()

            # System info
            uptime_seconds = synology.information.uptime
            days, remainder = divmod(uptime_seconds, 86400)
            hours, remainder = divmod(remainder, 3600)
            minutes, _ = divmod(remainder, 60)
            response = {
                "model": synology.information.model,
                "ram_mb": synology.information.ram,
                "serial": synology.information.serial,
                "temperature": synology.information.temperature,
                "temperature_warn": synology.information.temperature_warn,
                "uptime_days": days,
                "uptime_hours": hours,
                "uptime_minutes": minutes,
                "dsm_version": synology.information.version_string,
                "cpu_percent": synology.utilisation.cpu_total_load,
                "memory_percent": synology.utilisation.memory_real_usage,
                "net_up": synology.utilisation.network_up(),
                "net_down": synology.utilisation.network_down()
            }

            # Storage volumes
            volumes = []
            overall_bytes = 0
            overall_used_bytes = 0
            vol_name = ""
            for vol_id in synology.storage.volumes_ids:
                total_bytes = synology.storage.volume_size_total(vol_id)
                used_bytes = synology.storage.volume_size_used(vol_id)
                if total_bytes:
                    overall_bytes += total_bytes
                if used_bytes:
                    overall_used_bytes += used_bytes
                if vol_id == "volume_1":
                    vol_name = "nas"
                elif vol_id == "volume_2":
                    vol_name = "k8s-data"
                volumes.append({
                    "name": vol_name,
                    "id": vol_id,
                    "status": synology.storage.volume_status(vol_id),
                    "percent_used": synology.storage.volume_percentage_used(vol_id),
                    "size_total": round(total_bytes / (1024 ** 4), 2) if total_bytes else None,
                    "size_used": round(used_bytes / (1024 ** 4), 2) if used_bytes else None,
                })
            response["volumes"] = volumes

            response["overall_percent_used"] = int(round((overall_used_bytes / overall_bytes) * 100, 0)) \
                if overall_bytes > 0 else 0

            # Disks
            disks = []
            for disk_id in synology.storage.disks_ids:
                disks.append({
                    "id": disk_id,
                    "name": synology.storage.disk_name(disk_id),
                    "status": synology.storage.disk_status(disk_id),
                    "smart_status": synology.storage.disk_smart_status(disk_id),
                    "temperature": synology.storage.disk_temp(disk_id),
                })

            response["disks"] = disks
        except Exception as ex:
            payload['return_code']  = 500
            data = {}
            message = f"Exception collection Synology data"
            response["message"] = message
            stack_trace = traceback.format_exc()
            self._logger.message(message=message, exception=ex, stack_trace=stack_trace, data=data,
                                 transaction=source_transaction)
        self._logger.transaction_event(EventType.SPAN_END, transaction=source_transaction,
                                       payload=response, return_code=payload['return_code'] )
        return response

    def _load_data(self, data: dict, payload: dict) -> None:
        payload['return_code'] = 200
        response = None
        url = None
        source_transaction = self._logger.transaction_event(EventType.SPAN_START, payload=payload,
                                                            source_component="synology: Local Insert",
                                                            transaction=self._transaction)
        try:
            url = self._local_api_base_url
            response = requests.post(url, json=data)
            response.raise_for_status()
            payload['inserted'] = 1
        except Exception as ex:
            payload['return_code']  = 500
            data = {}
            message = f"Exception inserting Synology data locally"
            payload["message"] = message
            stack_trace = traceback.format_exc()
            if response:
                data['url']: url
                data['status_code'] = response.status_code
                data['response.text'] = response.json()
            self._logger.message(message=message, exception=ex, stack_trace=stack_trace, data=data,
                                 transaction=source_transaction)
        self._logger.transaction_event(EventType.SPAN_END, transaction=source_transaction,
                                       payload=payload, return_code=payload['return_code'] )


def main():
    load_dotenv()
    config = Config()
    network = SynologyCollector(config)
    network.process()


if __name__ == "__main__":
    main()
