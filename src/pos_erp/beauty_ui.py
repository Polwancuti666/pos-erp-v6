from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class BeautyDashboardTheme:
    primary: str = "#C9A96E"
    background: str = "#FDFBF7"
    accent: str = "#C08081"
    surface: str = "#ffffff"
    text: str = "#2C2C2E"
    text_secondary: str = "#6E6E73"
    charcoal: str = "#1C1C1E"
    gold: str = "#C9A96E"
    gold_light: str = "#E8D5A8"
    radius_px: int = 20
    mood: str = "radiance-refinement"


def render_dashboard_html(*, branch_name: str) -> str:
    t = BeautyDashboardTheme()
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Member Glow Dashboard — Beauty & Shine</title>
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,600;0,700;1,400&family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        *, *::before, *::after {{ margin: 0; padding: 0; box-sizing: border-box; }}

        :root {{
            --ivory: {t.background};
            --ivory-warm: #F8F4ED;
            --gold: {t.gold};
            --gold-light: {t.gold_light};
            --charcoal: {t.charcoal};
            --rose: {t.accent};
            --text-primary: {t.text};
            --text-secondary: {t.text_secondary};
            --text-light: #AEAEB2;
        }}

        body {{
            font-family: 'Inter', -apple-system, sans-serif;
            background: var(--ivory);
            color: var(--text-primary);
            min-height: 100vh;
            -webkit-font-smoothing: antialiased;
        }}
        h1, h2, h3, h4 {{ font-family: 'Playfair Display', Georgia, serif; }}

        @keyframes shimmer {{
            0% {{ background-position: -200% center; }}
            100% {{ background-position: 200% center; }}
        }}
        .shimmer-text {{
            background: linear-gradient(90deg, var(--gold) 0%, var(--gold-light) 25%, #D4AF37 50%, var(--gold-light) 75%, var(--gold) 100%);
            background-size: 200% auto;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            animation: shimmer 4s linear infinite;
        }}

        @keyframes fadeInUp {{
            from {{ opacity: 0; transform: translateY(20px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        /* ── Nav ────────────────────────────────── */
        .nav {{
            background: white;
            border-bottom: 1px solid rgba(0,0,0,0.04);
            padding: 0 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            height: 64px;
        }}
        .nav-brand {{
            font-family: 'Playfair Display', serif;
            font-size: 1.2rem;
            color: var(--charcoal);
            font-weight: 700;
            text-decoration: none;
        }}
        .nav-brand span {{ color: var(--gold); }}
        .nav-links {{
            display: flex;
            gap: 1.5rem;
            list-style: none;
            align-items: center;
        }}
        .nav-links a {{
            text-decoration: none;
            color: var(--text-secondary);
            font-size: 0.85rem;
            font-weight: 500;
            transition: color 0.3s;
        }}
        .nav-links a:hover {{ color: var(--gold); }}
        .nav-links .active {{ color: var(--charcoal); font-weight: 600; }}

        /* ── Shell ──────────────────────────────── */
        .shell {{ padding: 2rem; max-width: 1200px; margin: 0 auto; }}

        /* ── Hero Card ──────────────────────────── */
        .hero {{
            background: linear-gradient(160deg, {t.charcoal} 0%, #3A3A3C 100%);
            color: white;
            border-radius: {t.radius_px}px;
            padding: 3rem;
            margin-bottom: 2rem;
            position: relative;
            overflow: hidden;
            animation: fadeInUp 0.6s ease;
        }}
        .hero::before {{
            content: '';
            position: absolute;
            top: -30%; right: -10%;
            width: 400px; height: 400px;
            background: radial-gradient(circle, rgba(201,169,110,0.12) 0%, transparent 70%);
            border-radius: 50%;
        }}
        .hero::after {{
            content: '';
            position: absolute;
            bottom: -20%; left: -5%;
            width: 300px; height: 300px;
            background: radial-gradient(circle, rgba(192,128,129,0.08) 0%, transparent 70%);
            border-radius: 50%;
        }}
        .hero-content {{ position: relative; z-index: 2; }}
        .hero-badge {{
            display: inline-block;
            padding: 0.4rem 1rem;
            border: 1px solid rgba(201,169,110,0.3);
            border-radius: 100px;
            font-size: 0.7rem;
            font-weight: 600;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            color: var(--gold-light);
            margin-bottom: 1rem;
        }}
        .hero h1 {{
            font-size: 2.2rem;
            margin-bottom: 0.5rem;
            letter-spacing: -0.02em;
        }}
        .hero p {{
            color: rgba(255,255,255,0.5);
            font-size: 0.95rem;
            font-weight: 300;
        }}
        .hero-stats {{
            display: flex;
            gap: 2.5rem;
            margin-top: 2rem;
            padding-top: 1.5rem;
            border-top: 1px solid rgba(255,255,255,0.06);
        }}
        .stat-item .stat-value {{
            font-family: 'Playfair Display', serif;
            font-size: 1.8rem;
            font-weight: 700;
            color: var(--gold-light);
        }}
        .stat-item .stat-label {{
            font-size: 0.75rem;
            color: rgba(255,255,255,0.4);
            margin-top: 0.2rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }}

        /* ── Metric Cards ───────────────────────── */
        .metrics {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }}
        .metric-card {{
            background: white;
            border-radius: {t.radius_px}px;
            padding: 1.8rem;
            border: 1px solid rgba(0,0,0,0.04);
            transition: all 0.3s;
            animation: fadeInUp 0.6s ease;
        }}
        .metric-card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 12px 32px rgba(0,0,0,0.06);
        }}
        .metric-icon {{
            width: 44px; height: 44px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.3rem;
            background: var(--ivory-warm);
            margin-bottom: 1rem;
        }}
        .metric-value {{
            font-family: 'Playfair Display', serif;
            font-size: 1.8rem;
            font-weight: 700;
            color: var(--charcoal);
            margin-bottom: 0.2rem;
        }}
        .metric-label {{
            font-size: 0.8rem;
            color: var(--text-secondary);
            font-weight: 400;
        }}
        .metric-trend {{
            display: inline-block;
            margin-top: 0.6rem;
            padding: 0.2rem 0.6rem;
            border-radius: 100px;
            font-size: 0.7rem;
            font-weight: 600;
        }}
        .trend-up {{
            background: rgba(52,199,89,0.1);
            color: #34C759;
        }}
        .trend-neutral {{
            background: rgba(201,169,110,0.1);
            color: var(--gold);
        }}

        /* ── Section ────────────────────────────── */
        .section {{
            background: white;
            border-radius: {t.radius_px}px;
            padding: 2rem;
            border: 1px solid rgba(0,0,0,0.04);
            margin-bottom: 1.5rem;
            animation: fadeInUp 0.6s ease;
        }}
        .section-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.5rem;
        }}
        .section-header h3 {{
            font-size: 1.2rem;
            color: var(--charcoal);
        }}
        .section-header .badge {{
            padding: 0.3rem 0.8rem;
            border-radius: 100px;
            font-size: 0.7rem;
            font-weight: 600;
            background: var(--ivory-warm);
            color: var(--text-secondary);
        }}

        /* ── Activity Table ─────────────────────── */
        .activity-table {{
            width: 100%;
            border-collapse: collapse;
        }}
        .activity-table th {{
            text-align: left;
            padding: 0.8rem 1rem;
            font-size: 0.7rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: var(--text-light);
            border-bottom: 1px solid rgba(0,0,0,0.04);
        }}
        .activity-table td {{
            padding: 1rem;
            font-size: 0.85rem;
            border-bottom: 1px solid rgba(0,0,0,0.02);
            color: var(--text-primary);
        }}
        .activity-table tr:hover td {{
            background: var(--ivory);
        }}
        .status-badge {{
            display: inline-block;
            padding: 0.2rem 0.7rem;
            border-radius: 100px;
            font-size: 0.7rem;
            font-weight: 600;
        }}
        .status-completed {{
            background: rgba(52,199,89,0.1);
            color: #34C759;
        }}
        .status-active {{
            background: rgba(201,169,110,0.1);
            color: var(--gold);
        }}
        .status-pending {{
            background: rgba(174,174,178,0.1);
            color: var(--text-light);
        }}

        /* ── Quick Actions ──────────────────────── */
        .quick-actions {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 1rem;
        }}
        .action-card {{
            background: var(--ivory);
            border-radius: 14px;
            padding: 1.5rem;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s;
            text-decoration: none;
            color: inherit;
            border: 1px solid transparent;
        }}
        .action-card:hover {{
            border-color: var(--gold-light);
            background: rgba(201,169,110,0.04);
            transform: translateY(-2px);
        }}
        .action-card .icon {{ font-size: 1.8rem; margin-bottom: 0.6rem; }}
        .action-card .label {{
            font-size: 0.8rem;
            font-weight: 500;
            color: var(--text-primary);
        }}

        /* ── Footer ─────────────────────────────── */
        .dashboard-footer {{
            text-align: center;
            padding: 2rem;
            color: var(--text-light);
            font-size: 0.75rem;
        }}

        @media (max-width: 768px) {{
            .shell {{ padding: 1rem; }}
            .hero {{ padding: 2rem; }}
            .hero-stats {{ flex-wrap: wrap; gap: 1.5rem; }}
            .metrics {{ grid-template-columns: 1fr; }}
            .nav-links {{ display: none; }}
        }}
    </style>
</head>
<body>

<nav class="nav">
    <a href="/" class="nav-brand">Beauty <span>&</span> Shine</a>
    <ul class="nav-links">
        <li><a href="#" class="active">Dashboard</a></li>
        <li><a href="https://pos.beautynshine.web.id/">POS</a></li>
        <li><a href="/docs">API Docs</a></li>
        <li><a href="/">Home</a></li>
    </ul>
</nav>

<main class="shell">
    <!-- Hero -->
    <section class="hero">
        <div class="hero-content">
            <div class="hero-badge">✦ Member Glow Dashboard</div>
            <h1>Welcome back, <span class="shimmer-text">Owner</span></h1>
            <p>{branch_name} — Here's your daily radiance report.</p>
            <div class="hero-stats">
                <div class="stat-item">
                    <div class="stat-value">Rp 12.4M</div>
                    <div class="stat-label">Today's Revenue</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">47</div>
                    <div class="stat-label">Transactions</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">89%</div>
                    <div class="stat-label">Satisfaction</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">12</div>
                    <div class="stat-label">Active Staff</div>
                </div>
            </div>
        </div>
    </section>

    <!-- Metrics -->
    <div class="metrics">
        <div class="metric-card">
            <div class="metric-icon">🧖‍♀️</div>
            <div class="metric-value">156</div>
            <div class="metric-label">Facial Bookings</div>
            <span class="metric-trend trend-up">↑ 12% vs last week</span>
        </div>
        <div class="metric-card">
            <div class="metric-icon">💅</div>
            <div class="metric-value">89</div>
            <div class="metric-label">Nail Appointments</div>
            <span class="metric-trend trend-up">↑ 8% vs last week</span>
        </div>
        <div class="metric-card">
            <div class="metric-icon">🫧</div>
            <div class="metric-value">64</div>
            <div class="metric-label">Body Treatments</div>
            <span class="metric-trend trend-neutral">→ Stable</span>
        </div>
        <div class="metric-card">
            <div class="metric-icon">✨</div>
            <div class="metric-value">23</div>
            <div class="metric-label">New Members</div>
            <span class="metric-trend trend-up">↑ 24% vs last week</span>
        </div>
    </div>

    <!-- Recent Activity -->
    <div class="section">
        <div class="section-header">
            <h3>Recent Activity</h3>
            <span class="badge">Today</span>
        </div>
        <table class="activity-table">
            <thead>
                <tr>
                    <th>Client</th>
                    <th>Service</th>
                    <th>Staff</th>
                    <th>Amount</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>Anisa Putri</td>
                    <td>🧖‍♀️ Facial Treatment</td>
                    <td>Siti</td>
                    <td>Rp 150.000</td>
                    <td><span class="status-badge status-completed">Completed</span></td>
                </tr>
                <tr>
                    <td>Ratna Dewi</td>
                    <td>💆‍♀️ Creambath + Hair Spa</td>
                    <td>Dewi</td>
                    <td>Rp 250.000</td>
                    <td><span class="status-badge status-active">In Progress</span></td>
                </tr>
                <tr>
                    <td>Maya Sari</td>
                    <td>💅 Manicure + Pedicure</td>
                    <td>Siti</td>
                    <td>Rp 170.000</td>
                    <td><span class="status-badge status-completed">Completed</span></td>
                </tr>
                <tr>
                    <td>Lisa Anggraeni</td>
                    <td>🫧 Body Massage</td>
                    <td>Dewi</td>
                    <td>Rp 200.000</td>
                    <td><span class="status-badge status-pending">Scheduled</span></td>
                </tr>
            </tbody>
        </table>
    </div>

    <!-- Quick Actions -->
    <div class="section">
        <div class="section-header">
            <h3>Quick Actions</h3>
        </div>
        <div class="quick-actions">
            <a href="https://pos.beautynshine.web.id/" class="action-card">
                <div class="icon">🛍️</div>
                <div class="label">Open POS</div>
            </a>
            <a href="/docs" class="action-card">
                <div class="icon">📖</div>
                <div class="label">API Docs</div>
            </a>
            <a href="#" class="action-card">
                <div class="icon">👥</div>
                <div class="label">Manage Staff</div>
            </a>
            <a href="#" class="action-card">
                <div class="icon">📊</div>
                <div class="label">Reports</div>
            </a>
            <a href="#" class="action-card">
                <div class="icon">🎁</div>
                <div class="label">Loyalty Program</div>
            </a>
        </div>
    </div>

    <div class="dashboard-footer">
        Beauty & Shine · Radiance & Refinement · © 2026
    </div>
</main>

</body>
</html>"""
