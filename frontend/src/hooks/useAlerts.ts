import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchAlerts, fetchP1Alerts, fetchAlertsQueue, fetchAlertEscalations, acknowledgeAlert, escalateAlert, closeAlert } from '@/services/api/alerts';
import type { Alert, QueueSnapshot } from '@/types';

export function useAlerts() {
  const qc = useQueryClient();
  const q = useQuery<Alert[]>({ queryKey: ['alerts','list'], queryFn: fetchAlerts, staleTime: 5000, retry: 2, refetchInterval: 20_000 });
  const q1 = useQuery<Alert[]>({ queryKey: ['alerts','p1'], queryFn: fetchP1Alerts, staleTime: 5_000, retry: 2 });
  const queue = useQuery<QueueSnapshot>({ queryKey: ['alerts','queue'], queryFn: fetchAlertsQueue, staleTime: 10_000, retry: 2, refetchInterval: 30_000 });
  const escalations = useQuery<unknown[]>({ queryKey: ['alerts','escalations'], queryFn: fetchAlertEscalations, staleTime: 30_000, retry: 2, refetchInterval: 60_000 });

  const refresh = () => {
    qc.invalidateQueries();
  };

  const ack = useMutation({ mutationFn: (id: string) => acknowledgeAlert(id), onSuccess: refresh });
  const esc = useMutation({ mutationFn: (id: string) => escalateAlert(id), onSuccess: refresh });
  const closeM = useMutation({ mutationFn: (id: string) => closeAlert(id), onSuccess: refresh });

  return {
    ...q,
    p1: q1,
    queue,
    escalations,
    acknowledge: ack.mutateAsync,
    escalate: esc.mutateAsync,
    close: closeM.mutateAsync,
  };
}
