import { motion } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import { Settings as SettingsIcon, Bell, Shield, Eye, Database } from 'lucide-react';
import { useState } from 'react';
import { fetchSystemHealth } from '@/services/api';

export default function Settings() {
  const [notifications, setNotifications] = useState(true);
  const [autoEscalate, setAutoEscalate] = useState(true);
  const [riskThreshold, setRiskThreshold] = useState(75);
  const [darkMode] = useState(true);
  const { data: systemHealth, isLoading } = useQuery({
    queryKey: ['system', 'health'],
    queryFn: fetchSystemHealth,
    refetchInterval: 30000,
  });

  const runtimeHealthy = systemHealth?.readiness?.status === 'READY' && systemHealth?.modelHealth?.runtime_mode === 'FULL';

  return (
    <div className="p-6 space-y-6 max-w-3xl">
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
          <SettingsIcon className="w-6 h-6 text-primary" /> Settings
        </h1>
        <p className="text-sm text-muted-foreground mt-1">Configure dashboard preferences and alert thresholds</p>
      </motion.div>

      {/* Local UI Preferences */}
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="glass-panel p-5 space-y-4">
        <h3 className="text-sm font-semibold text-foreground flex items-center gap-2"><Bell className="w-4 h-4" /> Local UI Preferences</h3>
        <p className="text-xs text-muted-foreground">These preferences apply to the frontend only unless explicitly connected to a backend setting API.</p>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-foreground">Push Notifications</p>
            <p className="text-xs text-muted-foreground">Receive alerts for P1 priority cases</p>
          </div>
          <button onClick={() => setNotifications(!notifications)} className={`w-10 h-5 rounded-full transition-colors relative ${notifications ? 'bg-primary' : 'bg-muted'}`}>
            <div className={`w-4 h-4 rounded-full bg-foreground absolute top-0.5 transition-transform ${notifications ? 'translate-x-5' : 'translate-x-0.5'}`} />
          </button>
        </div>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-foreground">Auto-Escalation</p>
            <p className="text-xs text-muted-foreground">Automatically escalate alerts above threshold</p>
          </div>
          <button onClick={() => setAutoEscalate(!autoEscalate)} className={`w-10 h-5 rounded-full transition-colors relative ${autoEscalate ? 'bg-primary' : 'bg-muted'}`}>
            <div className={`w-4 h-4 rounded-full bg-foreground absolute top-0.5 transition-transform ${autoEscalate ? 'translate-x-5' : 'translate-x-0.5'}`} />
          </button>
        </div>
      </motion.div>

      {/* Risk Thresholds */}
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }} className="glass-panel p-5 space-y-4">
        <h3 className="text-sm font-semibold text-foreground flex items-center gap-2"><Shield className="w-4 h-4" /> Risk Thresholds</h3>
        <p className="text-xs text-muted-foreground">This threshold controls local UI filtering unless a backend policy API is connected later.</p>
        <div>
          <div className="flex justify-between text-sm mb-2">
            <span className="text-foreground">High Risk Threshold</span>
            <span className="text-risk-high font-bold">{riskThreshold}%</span>
          </div>
          <input type="range" min={50} max={95} value={riskThreshold} onChange={e => setRiskThreshold(Number(e.target.value))} className="w-full accent-primary" />
          <div className="flex justify-between text-xs text-muted-foreground mt-1">
            <span>50%</span><span>95%</span>
          </div>
        </div>
      </motion.div>

      {/* Display */}
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }} className="glass-panel p-5 space-y-4">
        <h3 className="text-sm font-semibold text-foreground flex items-center gap-2"><Eye className="w-4 h-4" /> Display</h3>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-foreground">Dark Mode</p>
            <p className="text-xs text-muted-foreground">Professional dark banking theme</p>
          </div>
          <div className="px-3 py-1 bg-primary/15 text-primary rounded-md text-xs font-medium">Active</div>
        </div>
      </motion.div>

      {/* Data */}
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }} className="glass-panel p-5 space-y-4">
        <h3 className="text-sm font-semibold text-foreground flex items-center gap-2"><Database className="w-4 h-4" /> Data Source</h3>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-foreground">Backend Connectivity</p>
            <p className="text-xs text-muted-foreground">
              {isLoading ? 'Checking AML service health...' : runtimeHealthy ? 'Connected to live AML backend services' : 'Backend ready state is degraded'}
            </p>
          </div>
          <div className={`px-3 py-1 rounded-md text-xs font-medium ${runtimeHealthy ? 'bg-risk-low/15 text-risk-low' : 'bg-risk-medium/15 text-risk-medium'}`}>
            {isLoading ? 'Checking' : runtimeHealthy ? 'Live' : 'Degraded'}
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3 text-xs text-muted-foreground">
          <div className="rounded-2xl border border-border/60 bg-card/50 p-3">
            <div className="uppercase tracking-[0.18em]">Readiness</div>
            <div className="mt-1 text-sm text-foreground">{systemHealth?.readiness?.status ?? 'UNKNOWN'}</div>
          </div>
          <div className="rounded-2xl border border-border/60 bg-card/50 p-3">
            <div className="uppercase tracking-[0.18em]">Sequence Model</div>
            <div className="mt-1 text-sm text-foreground">{systemHealth?.modelHealth?.sequence_model ?? 'UNKNOWN'}</div>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
