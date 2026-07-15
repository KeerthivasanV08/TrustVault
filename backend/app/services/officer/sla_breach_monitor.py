"""
SLA Breach Monitoring Service

Background task that:
- Checks alerts every minute
- Detects SLA breaches
- Updates alert status
- Publishes SLA breach events
- Tracks breach metrics
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any
import asyncio
from app.core.runtime_context import get_runtime_session_id
from app.services.alerts.alert_storage_service import read_csv, append_row
from app.services.alerts.sla_service import create_sla_record, check_sla_breach
from app.db.file_storage import log_control_decision
from app.realtime.transaction_memory_store import publish_event
import pandas as pd


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# SLA Policy
SLA_POLICY = {
    "P1": 15,      # 15 minutes
    "P2": 120,     # 2 hours
    "P3": 1440,    # 24 hours
}


class SLABreachMonitor:
    """Monitors and tracks SLA breaches"""

    def __init__(self):
        self.runtime_session_id = get_runtime_session_id()
        self._breached_alerts = set()
        self._monitor_task = None

    def start_monitoring(self):
        """Start background SLA monitoring task"""
        if self._monitor_task is None or self._monitor_task.done():
            self._monitor_task = asyncio.create_task(self._monitor_loop())

    def stop_monitoring(self):
        """Stop SLA monitoring task"""
        if self._monitor_task:
            self._monitor_task.cancel()
            self._monitor_task = None

    async def _monitor_loop(self):
        """Background loop that checks SLA every 60 seconds"""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                await self.check_all_sla_breaches()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in SLA monitor: {e}")
                await asyncio.sleep(60)

    async def check_all_sla_breaches(self) -> Dict[str, Any]:
        """Check all open/under_review alerts for SLA breaches"""
        results = {
            "total_checked": 0,
            "newly_breached": 0,
            "breached_alerts": []
        }

        try:
            # Check both transaction and onboarding alerts
            for alert_type in ["transaction", "onboarding"]:
                alerts = read_csv(f"{alert_type}_alerts")
                
                for alert in alerts:
                    alert_id = str(alert.get("alert_id", ""))
                    if not alert_id:
                        continue

                    state = alert.get("state", "").upper()
                    if state not in ["OPEN", "UNDER_REVIEW", "ESCALATED"]:
                        continue

                    results["total_checked"] += 1

                    # Check SLA
                    sla_check = check_sla_breach(alert_id)
                    if sla_check.get("breached") and alert_id not in self._breached_alerts:
                        # New breach
                        self._breached_alerts.add(alert_id)
                        results["newly_breached"] += 1
                        
                        # Update alert status to SLA_BREACHED
                        await self._mark_sla_breached(alert_id, alert_type, alert, sla_check)
                        
                        results["breached_alerts"].append({
                            "alert_id": alert_id,
                            "priority": alert.get("priority", ""),
                            "remaining_seconds": sla_check.get("remaining_seconds")
                        })

        except Exception as e:
            print(f"Error checking SLA breaches: {e}")

        return results

    async def _mark_sla_breached(
        self,
        alert_id: str,
        alert_type: str,
        alert: Dict[str, Any],
        sla_check: Dict[str, Any]
    ) -> None:
        """Mark alert as SLA breached and publish events"""
        try:
            # Update alert status
            alerts = read_csv(f"{alert_type}_alerts")
            for a in alerts:
                if str(a.get("alert_id", "")) == str(alert_id):
                    a["state"] = "SLA_BREACHED"
                    a["updated_at"] = _now()
                    break

            # Write back
            df = pd.DataFrame(alerts)
            from app.services.alerts.alert_storage_service import _file_path, DEFAULT_HEADERS, _atomic_write_csv
            path = _file_path(f"{alert_type}_alerts")
            headers = DEFAULT_HEADERS.get(f"{alert_type}_alerts", [])
            for col in headers:
                if col not in df.columns:
                    df[col] = ""
            df = df[headers]
            _atomic_write_csv(df, path)

            # Log SLA breach
            log_control_decision({
                "event": "SLA_BREACH",
                "alert_id": alert_id,
                "actor": "SYSTEM",
                "entity_type": "ALERT",
                "old_state": alert.get("state", "UNKNOWN"),
                "new_state": "SLA_BREACHED",
                "reason": f"SLA exceeded by {abs(sla_check.get('remaining_seconds', 0))} seconds",
                "timestamp": _now(),
                "runtime_session_id": self.runtime_session_id
            })

            # Record SLA breach
            append_row("sla_tracking", {
                "alert_id": alert_id,
                "priority": alert.get("priority", ""),
                "sla_minutes": SLA_POLICY.get(alert.get("priority", "P3"), 1440),
                "created_at": alert.get("created_at", _now()),
                "due_at": (datetime.now(timezone.utc) - timedelta(seconds=abs(sla_check.get("remaining_seconds", 0)))).isoformat(),
                "breached": True,
                "last_checked": _now(),
                "runtime_session_id": self.runtime_session_id
            })

            # Publish SLA breach event
            try:
                await publish_event({
                    "type": "SLA_BREACHED",
                    "alert_id": alert_id,
                    "priority": alert.get("priority", ""),
                    "delay_seconds": abs(sla_check.get("remaining_seconds", 0)),
                    "timestamp": _now(),
                    "runtime_session_id": self.runtime_session_id
                })
            except Exception:
                pass

        except Exception as e:
            print(f"Error marking SLA breached: {e}")

    def get_breached_alerts(self) -> List[Dict[str, Any]]:
        """Get all currently breached alerts"""
        breached = []
        try:
            for alert_type in ["transaction", "onboarding"]:
                alerts = read_csv(f"{alert_type}_alerts")
                for alert in alerts:
                    if alert.get("state", "").upper() == "SLA_BREACHED":
                        breached.append({
                            "alert_id": alert.get("alert_id", ""),
                            "priority": alert.get("priority", ""),
                            "alert_type": alert_type,
                            "created_at": alert.get("created_at", ""),
                            "updated_at": alert.get("updated_at", "")
                        })
        except Exception as e:
            print(f"Error getting breached alerts: {e}")

        return breached


# Global instance
sla_breach_monitor = SLABreachMonitor()
