# Operations Deliverable - Round 1

## Status
- **Infrastructure Changes:** None required for this text-only capability overview.
- **Monitoring/Automation:** No immediate action needed.
- **Review:** Approved with no blockers.

## Operations Capability Text (PT-BR)
Posso ajudar com:
- **Operacoes** — Automacao de processos, monitoramento de infraestrutura, CI/CD pipelines, manutencao de servidores e otimizacao de deployments.

## Runbook Template: Agent Health-Check Monitoring

> Template for future use when automated agent workflows or scheduled heartbeat checks are implemented.

### Purpose
Monitor agent process health, uptime, and response latency across managed instances.

### Check Sequence
1. **Process Check** — Verify agent process is running (`systemctl status` / `pm2 status` / container health).
2. **Heartbeat Ping** — Send HTTP GET to `/health` endpoint; expect 200 within 5s timeout.
3. **Log Tail** — Inspect last 50 lines of agent logs for ERROR/FATAL entries.
4. **Resource Usage** — Check CPU/memory against thresholds (CPU < 80%, MEM < 85%).
5. **Escalation** — If any check fails 3 consecutive times, trigger alert (webhook/email).

### Alert Channels
- Primary: Webhook notification to ops channel
- Secondary: Email to on-call

### Recovery Actions
- Auto-restart agent process on heartbeat failure
- Scale horizontally if resource threshold exceeded for >5min

## Future Subtasks Log
- [ ] **Automation:** Implement automated agent health-check monitoring when heartbeat endpoints are deployed.
- [ ] **Runbook:** Expand runbook with real endpoint URLs and alert webhook configs once infrastructure is provisioned.
- [ ] **DevSecOps:** Add security audit pipeline and infrastructure hardening checklist as sixth capability domain.
