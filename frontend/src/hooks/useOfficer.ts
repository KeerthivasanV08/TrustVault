import { useMutation, useQueryClient } from '@tanstack/react-query';
import { review, freeze, sar, escalate, whitelistOfficer } from '@/services/api/officer';

export function useOfficerActions() {
  const qc = useQueryClient();
  const refresh = () => {
    qc.invalidateQueries();
  };

  const reviewM = useMutation({ mutationFn: (p: any) => review(p), onSuccess: refresh });
  const freezeM = useMutation({ mutationFn: (p: any) => freeze(p), onSuccess: refresh });
  const sarM = useMutation({ mutationFn: (p: any) => sar(p), onSuccess: refresh });
  const escalateM = useMutation({ mutationFn: (p: any) => escalate(p), onSuccess: refresh });
  const whitelistM = useMutation({ mutationFn: (p: any) => whitelistOfficer(p), onSuccess: refresh });

  return {
    review: reviewM.mutateAsync,
    freeze: freezeM.mutateAsync,
    sar: sarM.mutateAsync,
    escalate: escalateM.mutateAsync,
    whitelist: whitelistM.mutateAsync,
  };
}
