# HiveClip - Plano de Implementacao

## Visao Geral

Produto novo baseado no Paperclip que orquestra ambientes Windows dedicados por board.
Cada board = 1 VM Windows no Vultr com Paperclip local rodando.
O usuario ve tudo como um produto unico e fluido.

```
USUARIO
   |
   v
[HiveClip Control Plane]  <-- Node.js centralizado
   |        |        |
   v        v        v
[VM Win]  [VM Win]  [VM Win]   <-- Vultr VMs
 Board1    Board2    Board3
 Paperclip Paperclip Paperclip
 VNC       VNC       VNC
```

---

## Arquitetura

### Control Plane (centralizado)
- Auth / Users / Billing
- VM lifecycle (Vultr API - criar, pausar, deletar, listar)
- Proxy reverso para API de cada Paperclip remoto
- WebSocket proxy (VNC via noVNC + Paperclip live events)
- Dashboard agregado (status de todas as VMs/boards)

### Data Plane (por VM)
- Windows Server 2022/2025 no Vultr
- Paperclip rodando local (:3100)
- TigerVNC Server (:5900)
- Agentes (Claude Code, Codex, etc) rodando local

### Frontend (unico)
- Fork da UI do Paperclip (React 19, Vite, Tailwind CSS 4, Radix UI)
- CompanyRail agora mostra boards = VMs
- Aba "Desktop" com noVNC embutido
- Status da VM no sidebar (provisioning, running, stopped, error)
- Mesma linguagem visual (OKLCH colors, Lucide icons, dark mode first)

---

## Tech Stack

| Camada | Tecnologia |
|--------|-----------|
| Frontend | React 19 + Vite 6 + Tailwind CSS 4 + Radix UI (fork do Paperclip) |
| Control Plane API | Node.js + Express 5 + TypeScript |
| Database | PostgreSQL (embedded ou externo) + Drizzle ORM |
| VM Provider | Vultr API v2 |
| Provisioning | WinRM (PowerShell remoto) |
| VNC | TigerVNC Server (VM) + noVNC (frontend) + WebSocket proxy |
| Auth | Better Auth (JWT) |
| Monitoramento | Heartbeat polling + WebSocket events |

---

## Estrutura do Projeto

```
hiveclip/
├── package.json
├── pnpm-workspace.yaml
├── tsconfig.json
│
├── packages/
│   ├── db/                        # Drizzle schema + migrations
│   │   └── src/
│   │       ├── schema/
│   │       │   ├── users.ts
│   │       │   ├── boards.ts      # board = company + VM metadata
│   │       │   ├── vms.ts         # VM lifecycle, IP, status, credentials
│   │       │   ├── board-memberships.ts
│   │       │   └── activity-log.ts
│   │       ├── migrations/
│   │       └── client.ts
│   │
│   ├── shared/                    # Tipos compartilhados front/back
│   │   └── src/
│   │       ├── types.ts           # Board, VM, User types
│   │       ├── validators.ts      # Zod schemas
│   │       ├── vm-states.ts       # Estado finito da VM
│   │       └── api.ts             # Tipos de request/response
│   │
│   └── vultr/                     # Vultr API client isolado
│       └── src/
│           ├── client.ts          # API wrapper tipado
│           ├── plans.ts           # Logica de selecao de plano
│           ├── provisioner.ts     # WinRM + scripts PowerShell
│           └── types.ts
│
├── server/                        # Control Plane API
│   └── src/
│       ├── index.ts               # Bootstrap
│       ├── app.ts                 # Express app setup
│       ├── config.ts              # Config do control plane
│       │
│       ├── middleware/
│       │   ├── auth.ts            # Better Auth middleware
│       │   ├── error-handler.ts
│       │   ├── logger.ts
│       │   └── proxy.ts           # Proxy middleware para VMs
│       │
│       ├── routes/
│       │   ├── health.ts
│       │   ├── auth.ts            # Login, registro, sessao
│       │   ├── boards.ts          # CRUD de boards
│       │   ├── vms.ts             # Status, start, stop, reboot
│       │   ├── provisioning.ts    # SSE de progresso
│       │   ├── vnc-proxy.ts       # WebSocket upgrade -> VNC
│       │   └── proxy.ts          # Catch-all proxy para Paperclip API
│       │
│       ├── services/
│       │   ├── boards.ts          # Logica de negocio de boards
│       │   ├── vms.ts             # Lifecycle de VMs (Vultr)
│       │   ├── provisioning.ts    # Orquestracao de instalacao
│       │   ├── proxy.ts           # HTTP proxy para Paperclip remoto
│       │   ├── vnc.ts             # WebSocket proxy para VNC
│       │   └── health-monitor.ts  # Polling de saude das VMs
│       │
│       └── types/
│           └── express.d.ts
│
├── ui/                            # Frontend (fork do Paperclip UI)
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── index.css              # Mesmos design tokens do Paperclip
│       │
│       ├── components/
│       │   ├── ui/                # Copiados do Paperclip (21 componentes)
│       │   │   ├── button.tsx
│       │   │   ├── dialog.tsx
│       │   │   ├── input.tsx
│       │   │   └── ...
│       │   │
│       │   ├── Layout.tsx         # Adaptado: inclui VM status
│       │   ├── BoardRail.tsx      # Era CompanyRail, agora mostra VMs
│       │   ├── Sidebar.tsx        # Navegacao dentro do board
│       │   ├── VmStatusBadge.tsx  # Status visual da VM
│       │   ├── ProvisioningProgress.tsx  # Barra de progresso
│       │   ├── VncViewer.tsx      # noVNC wrapper React
│       │   └── ... (demais componentes do Paperclip adaptados)
│       │
│       ├── pages/
│       │   ├── Landing.tsx        # Signup/login
│       │   ├── BoardList.tsx      # Lista de boards (VMs)
│       │   ├── NewBoard.tsx       # Wizard de criacao (auto-provisiona)
│       │   ├── Dashboard.tsx      # Dashboard do board (proxy do Paperclip)
│       │   ├── Desktop.tsx        # noVNC full-screen
│       │   ├── Agents.tsx         # Proxy do Paperclip
│       │   ├── Issues.tsx         # Proxy do Paperclip
│       │   └── Settings.tsx       # Config do board + VM
│       │
│       ├── context/
│       │   ├── AuthContext.tsx
│       │   ├── BoardContext.tsx    # Era CompanyContext
│       │   ├── VmContext.tsx       # Estado da VM atual
│       │   └── ThemeContext.tsx
│       │
│       ├── api/
│       │   ├── client.ts          # HTTP client (mesmo padrao)
│       │   ├── boards.ts
│       │   ├── vms.ts
│       │   └── proxy.ts          # Calls que vao pro Paperclip via proxy
│       │
│       └── lib/
│           ├── utils.ts
│           ├── router.tsx
│           └── vm-states.ts
│
└── provisioning/                  # Scripts de bootstrap da VM
    ├── bootstrap.ps1              # Script principal (entry point)
    ├── install-node.ps1
    ├── install-paperclip.ps1
    ├── install-vnc.ps1
    ├── configure-firewall.ps1
    ├── install-claude-code.ps1
    └── create-services.ps1        # Scheduled tasks para auto-start
```

---

## Schema do Banco (Control Plane)

```sql
-- Usuarios do HiveClip
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  display_name TEXT,
  role TEXT DEFAULT 'user',  -- 'admin' | 'user'
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Boards (cada um = 1 VM + 1 instancia Paperclip)
CREATE TABLE boards (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_id UUID NOT NULL REFERENCES users(id),
  name TEXT NOT NULL,
  description TEXT,
  status TEXT DEFAULT 'provisioning',
  -- 'provisioning' | 'starting' | 'running' | 'stopped' | 'error' | 'destroying'
  brand_color TEXT,
  issue_prefix TEXT UNIQUE,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- VMs Vultr (1:1 com boards)
CREATE TABLE vms (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  board_id UUID UNIQUE NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
  vultr_instance_id TEXT UNIQUE,
  region TEXT NOT NULL,
  plan TEXT NOT NULL,
  os TEXT NOT NULL,
  ip_address TEXT,
  internal_ip TEXT,
  hostname TEXT,
  admin_password TEXT,  -- criptografado
  vnc_port INTEGER DEFAULT 5900,
  paperclip_port INTEGER DEFAULT 3100,
  vultr_status TEXT,    -- raw status da Vultr API
  power_status TEXT,    -- 'running' | 'stopped'
  server_status TEXT,   -- 'ok' | 'installingbooting' | 'locked'
  paperclip_healthy BOOLEAN DEFAULT FALSE,
  vnc_healthy BOOLEAN DEFAULT FALSE,
  last_health_check TIMESTAMPTZ,
  provisioning_step TEXT,
  provisioning_progress INTEGER DEFAULT 0,
  provisioning_total INTEGER DEFAULT 12,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Board memberships (quem pode acessar qual board)
CREATE TABLE board_memberships (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  board_id UUID NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES users(id),
  role TEXT DEFAULT 'member',  -- 'owner' | 'admin' | 'member' | 'viewer'
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(board_id, user_id)
);

-- Log de atividade do control plane
CREATE TABLE activity_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  board_id UUID REFERENCES boards(id) ON DELETE SET NULL,
  user_id UUID REFERENCES users(id),
  action TEXT NOT NULL,
  -- 'board.created' | 'vm.provisioned' | 'vm.started' | 'vm.stopped' | etc
  details JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

---

## Fases de Implementacao

### FASE 0 - Setup do Projeto (1-2 dias)
- [ ] Criar repo hiveclip
- [ ] Setup monorepo pnpm (workspace, tsconfig, vitest)
- [ ] Copiar componentes UI do Paperclip (ui/components, design tokens, index.css)
- [ ] Copiar packages/shared como base de tipos
- [ ] Setup packages/db com Drizzle + embedded PostgreSQL
- [ ] Setup server basico (Express 5, pino, error handler)
- [ ] Verificar que o design system funciona (dark mode, componentes, icons)

### FASE 1 - Auth + Boards CRUD (2-3 dias)
- [ ] Implementar auth (Better Auth - registro, login, sessao)
- [ ] Schema boards + board_memberships
- [ ] API: POST /api/boards (criar board)
- [ ] API: GET /api/boards (listar boards do usuario)
- [ ] API: GET /api/boards/:id
- [ ] API: PATCH /api/boards/:id
- [ ] API: DELETE /api/boards/:id
- [ ] UI: Pagina de login/registro
- [ ] UI: BoardRail (sidebar com lista de boards)
- [ ] UI: BoardContext (selecao de board ativo)
- [ ] UI: Layout basico (rail + sidebar + content area)

### FASE 2 - Vultr Integration + VM Lifecycle (3-4 dias)
- [ ] Copiar e adaptar vultr-service.ts para packages/vultr/
- [ ] Tipar com TypeScript (era JS puro)
- [ ] Logica de selecao automatica do melhor plano Windows
- [ ] Logica de selecao automatica da melhor regiao (latencia)
- [ ] Geracao automatica de senha segura
- [ ] API: POST /api/boards/:id/provision (inicia criacao da VM)
- [ ] API: GET /api/boards/:id/vm (status da VM)
- [ ] API: POST /api/boards/:id/vm/start
- [ ] API: POST /api/boards/:id/vm/stop
- [ ] API: POST /api/boards/:id/vm/reboot
- [ ] API: DELETE /api/boards/:id/vm (destroy)
- [ ] Schema vms + migrations
- [ ] SSE endpoint para progresso do provisioning
- [ ] UI: ProvisioningProgress (barra animada com steps)
- [ ] UI: VmStatusBadge no BoardRail
- [ ] Health monitor service (polling periodico de saude)

### FASE 3 - Provisioning Automatico (3-4 dias)
- [ ] Script bootstrap.ps1 (entry point via WinRM)
- [ ] Instalar Node.js via WinRM
- [ ] Instalar Git via WinRM
- [ ] Clonar + instalar Paperclip na VM via WinRM
- [ ] Configurar Paperclip (local_trusted mode, porta 3100)
- [ ] Aplicar migrations do Paperclip automaticamente
- [ ] Instalar TigerVNC Server via WinRM
- [ ] Configurar firewall (abrir 3100, 5900)
- [ ] Criar scheduled tasks (auto-start Paperclip + VNC)
- [ ] Instalar Claude Code CLI
- [ ] Health check final (Paperclip + VNC respondendo)
- [ ] Atualizar status no banco: board -> 'running'

### FASE 4 - Proxy Reverso para Paperclip (2-3 dias)
- [ ] Middleware proxy: /api/boards/:boardId/paperclip/* -> VM:3100/api/*
- [ ] Resolver boardId -> IP da VM
- [ ] Forward headers (auth, content-type)
- [ ] Forward query params
- [ ] Suporte a multipart/form-data (uploads)
- [ ] Cache de conexoes por VM
- [ ] Timeout e retry em caso de VM lenta
- [ ] Error handling (VM offline -> mensagem amigavel)
- [ ] WebSocket proxy para eventos live do Paperclip

### FASE 5 - UI do Board (proxied) (3-4 dias)
- [ ] Adaptar paginas do Paperclip para usar proxy API
- [ ] Dashboard.tsx (proxied do Paperclip remoto)
- [ ] Agents.tsx (lista + detail, proxied)
- [ ] Issues.tsx (lista + detail + kanban, proxied)
- [ ] Goals.tsx (proxied)
- [ ] Activity.tsx (proxied)
- [ ] Sidebar navegacao dentro do board
- [ ] Live updates via WebSocket proxy
- [ ] Onboarding wizard adaptado (criar company + primeiro agente no Paperclip remoto)

### FASE 6 - VNC Desktop View (2-3 dias)
- [ ] Instalar noVNC no frontend (npm @nicecv/novnc ou build custom)
- [ ] WebSocket proxy: /api/boards/:boardId/vnc -> VM:5900
- [ ] VncViewer.tsx component (React wrapper do noVNC)
- [ ] Desktop.tsx page (full viewport noVNC)
- [ ] Tab "Desktop" no sidebar
- [ ] Toolbar: clipboard sync, ctrl+alt+del, fullscreen
- [ ] Reconnect automatico em caso de perda de conexao
- [ ] Indicador de qualidade da conexao

### FASE 7 - Fluxo Completo de Signup (1-2 dias)
- [ ] Landing page
- [ ] Signup -> auto-cria primeiro board
- [ ] Board criado -> auto-provisiona VM
- [ ] Provisioning completo -> redireciona para o board
- [ ] Onboarding wizard do Paperclip (criar CEO, etc)
- [ ] Loading state durante provisioning (animacao bonita)
- [ ] Fallback se provisioning falhar (retry, suporte)

### FASE 8 - Multi-Board Experience (1-2 dias)
- [ ] Criar novo board (adiciona VM)
- [ ] Trocar entre boards fluido (BoardRail)
- [ ] Status de cada VM no rail (dot colorido: verde, amarelo, vermelho)
- [ ] Pausar/retomar VMs (economia de custo)
- [ ] Excluir board (confirmar -> destroy VM)
- [ ] Limites por usuario (max boards por plano)

### FASE 9 - Polish + Deploy (2-3 dias)
- [ ] Dockerfile do Control Plane
- [ ] Docker Compose (control plane + postgres)
- [ ] HTTPS / Cloudflare tunnel
- [ ] Rate limiting
- [ ] Logging estruturado
- [ ] Metricas (VMs ativas, custo total, uptime)
- [ ] Error boundaries no frontend
- [ ] Mobile responsive
- [ ] Testes E2E criticos (signup, provisioning, proxy)

---

## Fluxo do Usuario (end-to-end)

```
1. Acessa hiveclip.com
2. Cria conta (email + senha)
3. Automaticamente:
   - Cria board "My First Board"
   - Seleciona melhor plano Windows no Vultr
   - Seleciona regiao mais proxima
   - Gera senha admin
   - Cria VM
4. Tela de provisioning (barra de progresso):
   - "Criando servidor..."
   - "Aguardando inicializacao..."
   - "Instalando Node.js..."
   - "Instalando Paperclip..."
   - "Configurando VNC..."
   - "Instalando Claude Code..."
   - "Finalizando..."
5. Redireciona para o board
6. Ve o dashboard do Paperclip (via proxy)
7. Pode clicar em "Desktop" para ver a VM via VNC
8. Pode criar agentes, issues, goals, etc
9. Tudo roda na VM dedicada
10. Pode criar outro board (+) -> repete 3-5
11. Troca entre boards pelo BoardRail
```

---

## Decisoes Tecnicas

### Proxy vs Iframe
**Decisao: Proxy**
- Iframe teria problemas de CORS, auth, e quebra a experiencia
- Proxy permite controle total sobre a UX
- Frontend faz chamadas para o control plane que roteia para a VM certa

### VNC: noVNC vs RDP via browser
**Decisao: noVNC**
- noVNC e open source, leve, WebSocket nativo
- Funciona em qualquer browser sem plugin
- TigerVNC server e free e estavel no Windows

### Estado da VM: polling vs push
**Decisao: Hibrido**
- Health monitor faz polling a cada 30s para cada VM ativa
- Frontend recebe updates via SSE durante provisioning
- WebSocket para live events do Paperclip (proxy)

### Senha da VM
**Decisao: Auto-gerada + criptografada**
- Gera senha forte (32 chars, mixed case + numbers + symbols)
- Armazena criptografada no banco (AES-256)
- Usuario pode ver/copiar na UI se precisar (para RDP manual)
- Nunca trafega em plaintext nos logs

### Selecao de plano Vultr
**Decisao: Automatica**
- Filtra: Windows compativel, VC2, <= $60/mes
- Ordena por melhor custo-beneficio (RAM/vCPU por dolar)
- Seleciona o melhor automaticamente
- Usuario NAO escolhe (simplifica UX)

---

## Estimativa

| Fase | Dias | Descricao |
|------|------|-----------|
| 0 | 1-2 | Setup projeto |
| 1 | 2-3 | Auth + Boards CRUD |
| 2 | 3-4 | Vultr + VM lifecycle |
| 3 | 3-4 | Provisioning automatico |
| 4 | 2-3 | Proxy reverso |
| 5 | 3-4 | UI do Board (proxied) |
| 6 | 2-3 | VNC Desktop view |
| 7 | 1-2 | Fluxo de signup |
| 8 | 1-2 | Multi-board |
| 9 | 2-3 | Polish + deploy |
| **Total** | **~21-30 dias** | |

---

## Riscos e Mitigacoes

| Risco | Impacto | Mitigacao |
|-------|---------|-----------|
| VM demora pra provisionar (10-15 min) | UX ruim | Loading animado + notificacao quando pronto |
| WinRM falha na conexao | Provisioning quebra | Retry com backoff + fallback manual |
| Latencia do proxy (control plane -> VM) | UI lenta | Cache, keep-alive, selecao de regiao proxima |
| VNC lento em conexoes ruins | Desktop inutilizavel | Compressao, quality adjustment, fallback para RDP file |
| Custo das VMs ($30-60/mes cada) | Billing alto | Pausar VMs ociosas, alertas de custo |
| Paperclip atualiza e quebra compat | Proxy quebra | Pinnar versao, testar updates antes |
